from __future__ import annotations

import argparse
import csv
import heapq
import json
import math
import os
import random
import struct
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from PIL import Image
except ImportError:  # Pillow нужен только для функций с изображениями
    Image = None


# ============================================================
# Общие утилиты
# ============================================================


def int_to_bytes(number: int, size: int) -> bytes:
    if number < 0:
        raise ValueError("number must be non-negative")
    return number.to_bytes(size, byteorder="big")


def bytes_to_int(data: bytes) -> int:
    return int.from_bytes(data, byteorder="big")


def print_hex(data: bytes) -> str:
    return " ".join(f"0x{b:02X}" for b in data)


def compression_ratio(original_size: int, compressed_size: int) -> float:
    return 0.0 if compressed_size == 0 else original_size / compressed_size


def require_symbol_aligned(data: bytes, symbol_size: int) -> None:
    if symbol_size <= 0:
        raise ValueError("symbol_size must be positive")
    if len(data) % symbol_size != 0:
        raise ValueError("data length must be divisible by symbol_size")


# ============================================================
# BitWriter / BitReader: чтение и запись битовых строк
# ============================================================


class BitWriter:
    def __init__(self) -> None:
        self._data = bytearray()
        self._current = 0
        self._used = 0
        self.bit_length = 0

    def write_bit(self, bit: int) -> None:
        bit = 1 if bit else 0
        self._current = (self._current << 1) | bit
        self._used += 1
        self.bit_length += 1
        if self._used == 8:
            self._data.append(self._current)
            self._current = 0
            self._used = 0

    def write_bits(self, bits: str) -> None:
        for ch in bits:
            if ch not in "01":
                raise ValueError("bits string must contain only 0 and 1")
            self.write_bit(1 if ch == "1" else 0)

    def write_int(self, value: int, bit_count: int) -> None:
        if value < 0 or value >= (1 << bit_count):
            raise ValueError("value does not fit bit_count")
        for shift in range(bit_count - 1, -1, -1):
            self.write_bit((value >> shift) & 1)

    def to_bytes(self) -> Tuple[bytes, int]:
        out = bytearray(self._data)
        if self._used:
            out.append(self._current << (8 - self._used))
        return bytes(out), self.bit_length


class BitReader:
    def __init__(self, data: bytes, bit_length: Optional[int] = None) -> None:
        self.data = data
        self.bit_length = len(data) * 8 if bit_length is None else bit_length
        if self.bit_length > len(data) * 8:
            raise ValueError("bit_length is larger than available data")
        self.pos = 0

    def read_bit(self) -> int:
        if self.pos >= self.bit_length:
            raise EOFError("no more bits")
        byte = self.data[self.pos // 8]
        bit = (byte >> (7 - (self.pos % 8))) & 1
        self.pos += 1
        return bit

    def read_bits(self, count: int) -> str:
        return "".join(str(self.read_bit()) for _ in range(count))

    def read_int(self, bit_count: int) -> int:
        value = 0
        for _ in range(bit_count):
            value = (value << 1) | self.read_bit()
        return value

    def has_more(self) -> bool:
        return self.pos < self.bit_length


BIT_MAGIC = b"BITS"
BIT_HEADER_FORMAT = ">4sQ"
BIT_HEADER_SIZE = struct.calcsize(BIT_HEADER_FORMAT)


def write_bitstring_file(path: str | os.PathLike, bits: str) -> None:
    writer = BitWriter()
    writer.write_bits(bits)
    payload, bit_len = writer.to_bytes()
    with open(path, "wb") as f:
        f.write(struct.pack(BIT_HEADER_FORMAT, BIT_MAGIC, bit_len))
        f.write(payload)


def read_bitstring_file(path: str | os.PathLike) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) < BIT_HEADER_SIZE:
        raise ValueError("bitstring file is too short")
    magic, bit_len = struct.unpack(BIT_HEADER_FORMAT, raw[:BIT_HEADER_SIZE])
    if magic != BIT_MAGIC:
        raise ValueError("invalid bitstring file")
    reader = BitReader(raw[BIT_HEADER_SIZE:], bit_len)
    return reader.read_bits(bit_len)


# ============================================================
# RAW-формат изображений
# ============================================================


RAW_MAGIC = b"RAW1"
RAW_HEADER_FORMAT = ">4sBII"
RAW_HEADER_SIZE = struct.calcsize(RAW_HEADER_FORMAT)
RAW_BW = 0
RAW_GRAY = 1
RAW_RGB = 2


def image_to_raw(input_image: str | os.PathLike, output_raw: str | os.PathLike, image_type: int) -> None:
    if Image is None:
        raise ImportError("Install Pillow: pip install pillow")
    img = Image.open(input_image)
    if image_type == RAW_BW:
        img = img.convert("1").convert("L")
        pixels = img.tobytes()
    elif image_type == RAW_GRAY:
        img = img.convert("L")
        pixels = img.tobytes()
    elif image_type == RAW_RGB:
        img = img.convert("RGB")
        pixels = img.tobytes()
    else:
        raise ValueError("unknown image_type")
    width, height = img.size
    with open(output_raw, "wb") as f:
        f.write(struct.pack(RAW_HEADER_FORMAT, RAW_MAGIC, image_type, width, height))
        f.write(pixels)


def read_raw(raw_file: str | os.PathLike) -> Tuple[int, int, int, bytes]:
    with open(raw_file, "rb") as f:
        raw = f.read()
    if len(raw) < RAW_HEADER_SIZE:
        raise ValueError("RAW file is too short")
    magic, image_type, width, height = struct.unpack(RAW_HEADER_FORMAT, raw[:RAW_HEADER_SIZE])
    if magic != RAW_MAGIC:
        raise ValueError("invalid RAW file")
    pixels = raw[RAW_HEADER_SIZE:]
    expected = width * height * (3 if image_type == RAW_RGB else 1)
    if len(pixels) != expected:
        raise ValueError("invalid RAW payload size")
    return image_type, width, height, pixels


def raw_to_image(raw_file: str | os.PathLike, output_image: str | os.PathLike) -> None:
    if Image is None:
        raise ImportError("Install Pillow: pip install pillow")
    image_type, width, height, pixels = read_raw(raw_file)
    mode = "RGB" if image_type == RAW_RGB else "L"
    Image.frombytes(mode, (width, height), pixels).save(output_image)


def compare_image_and_raw(image_file: str | os.PathLike, raw_file: str | os.PathLike) -> Dict[str, float]:
    image_size = os.path.getsize(image_file)
    raw_size = os.path.getsize(raw_file)
    return {
        "image_size": image_size,
        "raw_size": raw_size,
        "raw_to_image_ratio": compression_ratio(raw_size, image_size),
        "image_to_raw_ratio": compression_ratio(image_size, raw_size),
    }


# ============================================================
# Подготовка тестовых данных
# ============================================================


def make_enwik7(enwik9_file: str | os.PathLike, enwik7_file: str | os.PathLike) -> None:
    with open(enwik9_file, "rb") as f:
        data = f.read(10_000_000)
    if len(data) != 10_000_000:
        raise ValueError("enwik9 file is smaller than 10,000,000 bytes")
    with open(enwik7_file, "wb") as f:
        f.write(data)


def make_random_binary(filename: str | os.PathLike, size: int = 1024 * 1024) -> None:
    with open(filename, "wb") as f:
        f.write(os.urandom(size))


def check_min_size(filename: str | os.PathLike, min_size: int) -> bool:
    return os.path.getsize(filename) >= min_size


# ============================================================
# RLE с Ms/Mc и literal-блоками
# ============================================================


def rle_max_count(mc: int) -> int:
    if mc <= 0:
        raise ValueError("mc must be positive")
    return (1 << (8 * mc - 1)) - 1


def rle_encode(data: bytes, ms: int = 1, mc: int = 1) -> bytes:
    if ms <= 0 or mc <= 0:
        raise ValueError("ms and mc must be positive")
    require_symbol_aligned(data, ms)
    if not data:
        return b""

    max_len = rle_max_count(mc)
    literal_flag = 1 << (8 * mc - 1)
    symbols = [data[i:i + ms] for i in range(0, len(data), ms)]
    encoded = bytearray()
    i = 0
    n = len(symbols)

    while i < n:
        run_len = 1
        while i + run_len < n and symbols[i + run_len] == symbols[i] and run_len < max_len:
            run_len += 1

        if run_len >= 2:
            encoded += int_to_bytes(run_len, mc)
            encoded += symbols[i]
            i += run_len
        else:
            start = i
            literal_len = 0
            while i < n and literal_len < max_len:
                temp_run = 1
                while i + temp_run < n and symbols[i + temp_run] == symbols[i] and temp_run < max_len:
                    temp_run += 1
                if temp_run >= 2:
                    break
                i += 1
                literal_len += 1
            if literal_len == 0:  # защитный случай, теоретически недостижим
                literal_len = 1
                i += 1
            encoded += int_to_bytes(literal_flag | literal_len, mc)
            encoded += b"".join(symbols[start:start + literal_len])

    return bytes(encoded)


def rle_decode(encoded: bytes, ms: int = 1, mc: int = 1) -> bytes:
    if ms <= 0 or mc <= 0:
        raise ValueError("ms and mc must be positive")
    if not encoded:
        return b""
    literal_flag = 1 << (8 * mc - 1)
    length_mask = literal_flag - 1
    decoded = bytearray()
    i = 0
    while i < len(encoded):
        if i + mc > len(encoded):
            raise ValueError("not enough bytes for RLE control")
        control = bytes_to_int(encoded[i:i + mc])
        i += mc
        count = control & length_mask
        if count == 0:
            raise ValueError("RLE block has zero length")
        if control & literal_flag:
            block_size = count * ms
            if i + block_size > len(encoded):
                raise ValueError("literal block exceeds encoded data")
            decoded += encoded[i:i + block_size]
            i += block_size
        else:
            if i + ms > len(encoded):
                raise ValueError("not enough bytes for repeated symbol")
            symbol = encoded[i:i + ms]
            i += ms
            decoded += symbol * count
    return bytes(decoded)


RLE_MAGIC = b"RLE1"
RLE_HEADER_FORMAT = ">4sBBQ"
RLE_HEADER_SIZE = struct.calcsize(RLE_HEADER_FORMAT)


def write_rle_file(input_name: str | os.PathLike, output_name: str | os.PathLike, ms: int = 1, mc: int = 1) -> None:
    data = Path(input_name).read_bytes()
    encoded = rle_encode(data, ms, mc)
    header = struct.pack(RLE_HEADER_FORMAT, RLE_MAGIC, ms, mc, len(data))
    Path(output_name).write_bytes(header + encoded)


def read_rle_file(input_name: str | os.PathLike) -> bytes:
    raw = Path(input_name).read_bytes()
    if len(raw) < RLE_HEADER_SIZE:
        raise ValueError("RLE file is too short")
    magic, ms, mc, original_size = struct.unpack(RLE_HEADER_FORMAT, raw[:RLE_HEADER_SIZE])
    if magic != RLE_MAGIC:
        raise ValueError("invalid RLE file")
    decoded = rle_decode(raw[RLE_HEADER_SIZE:], ms, mc)
    if len(decoded) != original_size:
        raise ValueError("decoded RLE size mismatch")
    return decoded


def decode_rle_file(input_name: str | os.PathLike, output_name: str | os.PathLike) -> None:
    Path(output_name).write_bytes(read_rle_file(input_name))


# ============================================================
# UTF-8 проблема и вариант решения
# ============================================================


def encode_text_as_utf32(text: str, mc: int = 1) -> bytes:
    return rle_encode(text.encode("utf-32le"), ms=4, mc=mc)


def decode_text_from_utf32(encoded: bytes, mc: int = 1) -> str:
    return rle_decode(encoded, ms=4, mc=mc).decode("utf-32le")


def rle_encode_utf8_codepoints(text: str, mc: int = 1) -> bytes:
    """RLE по Unicode-символам: переводим в UTF-32LE, чтобы один символ = 4 байта."""
    return encode_text_as_utf32(text, mc=mc)


# ============================================================
# Энтропия
# ============================================================


def calculate_entropy(data: bytes, symbol_size: int = 1) -> float:
    require_symbol_aligned(data, symbol_size)
    if not data:
        return 0.0
    symbols = [data[i:i + symbol_size] for i in range(0, len(data), symbol_size)]
    freq = Counter(symbols)
    total = len(symbols)
    return -sum((c / total) * math.log2(c / total) for c in freq.values())


def entropy_by_symbol_sizes(data: bytes, sizes: Sequence[int] = (1, 2, 3, 4)) -> Dict[int, float]:
    result = {}
    for size in sizes:
        usable = data[:len(data) - (len(data) % size)]
        result[size] = calculate_entropy(usable, size) if usable else 0.0
    return result


# ============================================================
# MTF
# ============================================================


def mtf_encode(data: bytes) -> bytes:
    alphabet = list(range(256))
    result = bytearray()
    for byte in data:
        idx = alphabet.index(byte)
        result.append(idx)
        alphabet.pop(idx)
        alphabet.insert(0, byte)
    return bytes(result)


def mtf_decode(encoded: bytes) -> bytes:
    alphabet = list(range(256))
    result = bytearray()
    for idx in encoded:
        byte = alphabet[idx]
        result.append(byte)
        alphabet.pop(idx)
        alphabet.insert(0, byte)
    return bytes(result)


# ============================================================
# Huffman и канонический Huffman
# ============================================================


@dataclass(order=True)
class _HeapItem:
    freq: int
    order: int
    node: object


@dataclass
class _HuffNode:
    symbol: Optional[int]
    left: Optional["_HuffNode"] = None
    right: Optional["_HuffNode"] = None


def build_huffman_tree(freq: Dict[int, int]) -> Optional[_HuffNode]:
    heap: List[_HeapItem] = []
    order = 0
    for symbol, count in sorted(freq.items()):
        if count > 0:
            heapq.heappush(heap, _HeapItem(count, order, _HuffNode(symbol)))
            order += 1
    if not heap:
        return None
    while len(heap) > 1:
        a = heapq.heappop(heap)
        b = heapq.heappop(heap)
        parent = _HuffNode(None, a.node, b.node)
        heapq.heappush(heap, _HeapItem(a.freq + b.freq, order, parent))
        order += 1
    return heap[0].node


def get_code_lengths_from_tree(tree: Optional[_HuffNode]) -> Dict[int, int]:
    lengths: Dict[int, int] = {}
    def walk(node: Optional[_HuffNode], depth: int) -> None:
        if node is None:
            return
        if node.symbol is not None:
            lengths[node.symbol] = max(1, depth)  # один уникальный символ получает код длины 1
            return
        walk(node.left, depth + 1)
        walk(node.right, depth + 1)
    walk(tree, 0)
    return lengths


def build_codes_from_tree(tree: Optional[_HuffNode]) -> Dict[int, str]:
    codes: Dict[int, str] = {}
    def walk(node: Optional[_HuffNode], prefix: str) -> None:
        if node is None:
            return
        if node.symbol is not None:
            codes[node.symbol] = prefix or "0"
            return
        walk(node.left, prefix + "0")
        walk(node.right, prefix + "1")
    walk(tree, "")
    return codes


def build_canonical_huffman_codes(lengths: Dict[int, int]) -> Dict[int, str]:
    pairs = sorted((length, symbol) for symbol, length in lengths.items() if length > 0)
    codes: Dict[int, str] = {}
    code = 0
    prev_len = 0
    for length, symbol in pairs:
        code <<= (length - prev_len)
        codes[symbol] = format(code, f"0{length}b")
        code += 1
        prev_len = length
    return codes


def probability_model_from_data(data: bytes) -> Dict[int, float]:
    if not data:
        return {}
    cnt = Counter(data)
    total = len(data)
    return {symbol: count / total for symbol, count in cnt.items()}


def code_lengths_from_probability_model(model: Dict[int, float]) -> Dict[int, int]:
    """Строим дерево по вероятностной модели. Для Хаффмана достаточно относительных весов."""
    scaled = {int(symbol): max(1, int(prob * 1_000_000_000)) for symbol, prob in model.items() if prob > 0}
    return get_code_lengths_from_tree(build_huffman_tree(scaled))


def huffman_encode(data: bytes, probability_model: Optional[Dict[int, float]] = None) -> Tuple[bytes, Dict[str, object]]:
    if not data:
        return b"", {"lengths": {}, "original_size": 0, "bit_length": 0}
    if probability_model is None:
        lengths = get_code_lengths_from_tree(build_huffman_tree(Counter(data)))
    else:
        lengths = code_lengths_from_probability_model(probability_model)
        missing = set(data) - set(lengths)
        if missing:
            raise ValueError(f"probability model does not contain symbols: {sorted(missing)[:10]}")
    codes = build_canonical_huffman_codes(lengths)
    writer = BitWriter()
    for byte in data:
        writer.write_bits(codes[byte])
    encoded, bit_length = writer.to_bytes()
    return encoded, {"lengths": lengths, "original_size": len(data), "bit_length": bit_length}


def huffman_decode(encoded_data: bytes, metadata: Dict[str, object]) -> bytes:
    lengths = {int(k): int(v) for k, v in metadata["lengths"].items()}  # type: ignore[index]
    original_size = int(metadata["original_size"])  # type: ignore[index]
    bit_length = int(metadata.get("bit_length", len(encoded_data) * 8))  # type: ignore[union-attr]
    if original_size == 0:
        return b""
    codes = build_canonical_huffman_codes(lengths)
    reverse = {code: symbol for symbol, code in codes.items()}
    reader = BitReader(encoded_data, bit_length)
    result = bytearray()
    current = ""
    while reader.has_more() and len(result) < original_size:
        current += str(reader.read_bit())
        if current in reverse:
            result.append(reverse[current])
            current = ""
    if len(result) != original_size:
        raise ValueError("Huffman decoded size mismatch")
    return bytes(result)


# Совместимые имена для старого кода
huffman_canonical_encode = huffman_encode
huffman_canonical_decode = huffman_decode


HA_MAGIC = b"HA01"
HA_HEADER_FORMAT = ">4sQH"
HA_HEADER_SIZE = struct.calcsize(HA_HEADER_FORMAT)


def write_huffman_file(input_name: str | os.PathLike, output_name: str | os.PathLike,
                       probability_model: Optional[Dict[int, float]] = None) -> None:
    data = Path(input_name).read_bytes()
    payload, meta = huffman_encode(data, probability_model)
    lengths: Dict[int, int] = meta["lengths"]  # type: ignore[assignment]
    # Метаданные: original_size, bit_length, количество символов, пары byte/length.
    header = struct.pack(HA_HEADER_FORMAT, HA_MAGIC, int(meta["original_size"]), len(lengths))
    table = bytearray()
    for symbol, length in sorted(lengths.items()):
        table += struct.pack(">BB", symbol, length)
    bit_len_bytes = struct.pack(">Q", int(meta["bit_length"]))
    Path(output_name).write_bytes(header + bit_len_bytes + bytes(table) + payload)


def read_huffman_file(input_name: str | os.PathLike) -> bytes:
    raw = Path(input_name).read_bytes()
    if len(raw) < HA_HEADER_SIZE + 8:
        raise ValueError("Huffman file is too short")
    magic, original_size, count = struct.unpack(HA_HEADER_FORMAT, raw[:HA_HEADER_SIZE])
    if magic != HA_MAGIC:
        raise ValueError("invalid Huffman file")
    bit_length = struct.unpack(">Q", raw[HA_HEADER_SIZE:HA_HEADER_SIZE + 8])[0]
    pos = HA_HEADER_SIZE + 8
    lengths: Dict[int, int] = {}
    for _ in range(count):
        if pos + 2 > len(raw):
            raise ValueError("truncated Huffman table")
        symbol, length = struct.unpack(">BB", raw[pos:pos + 2])
        lengths[symbol] = length
        pos += 2
    return huffman_decode(raw[pos:], {"lengths": lengths, "original_size": original_size, "bit_length": bit_length})


def decode_huffman_file(input_name: str | os.PathLike, output_name: str | os.PathLike) -> None:
    Path(output_name).write_bytes(read_huffman_file(input_name))


# ============================================================
# Арифметическое сжатие на double для эксперимента
# ============================================================


def arithmetic_encode_double(data: bytes, probability_model: Optional[Dict[int, float]] = None) -> Tuple[float, int]:
    """Отдает число double внутри финального интервала и длину сообщения.
    Функция учебная: показывает, что при росте длины строки границы быстро совпадают.
    """
    if not data:
        return 0.0, 0
    if probability_model is None:
        probability_model = probability_model_from_data(data)
    symbols = sorted(probability_model)
    cumulative: Dict[int, Tuple[float, float]] = {}
    acc = 0.0
    for s in symbols:
        p = probability_model[s]
        cumulative[s] = (acc, acc + p)
        acc += p
    low, high = 0.0, 1.0
    for b in data:
        if b not in cumulative:
            raise ValueError("symbol is absent in probability model")
        span = high - low
        c_low, c_high = cumulative[b]
        high = low + span * c_high
        low = low + span * c_low
        if low == high:
            break
    return (low + high) / 2.0, len(data)


def arithmetic_double_collision_length(data: bytes, probability_model: Optional[Dict[int, float]] = None) -> int:
    if probability_model is None:
        probability_model = probability_model_from_data(data)
    symbols = sorted(probability_model)
    cumulative: Dict[int, Tuple[float, float]] = {}
    acc = 0.0
    for s in symbols:
        p = probability_model[s]
        cumulative[s] = (acc, acc + p)
        acc += p
    low, high = 0.0, 1.0
    for idx, b in enumerate(data, 1):
        span = high - low
        c_low, c_high = cumulative[b]
        high = low + span * c_high
        low = low + span * c_low
        if low == high:
            return idx
    return -1


# ============================================================
# BWT: наивный, обратный, блочный
# ============================================================


def bwt_direct(data: bytes) -> Tuple[bytes, int]:
    n = len(data)
    if n == 0:
        return b"", 0
    rotations = [(data[i:] + data[:i], i) for i in range(n)]
    rotations.sort(key=lambda x: x[0])
    last = bytearray()
    original_row = 0
    for row, (rot, idx) in enumerate(rotations):
        last.append(rot[-1])
        if idx == 0:
            original_row = row
    return bytes(last), original_row


def bwt_inverse_naive(bwt_data: bytes, original_row: int) -> bytes:
    n = len(bwt_data)
    table = [b""] * n
    for _ in range(n):
        table = sorted(bytes([bwt_data[i]]) + table[i] for i in range(n))
    return table[original_row] if n else b""


def bwt_inverse_with_row(bwt_data: bytes, original_row: int) -> bytes:
    n = len(bwt_data)
    if n == 0:
        return b""
    if not 0 <= original_row < n:
        raise ValueError("original_row is out of range")
    counts = [0] * 256
    ranks = [0] * n
    for i, b in enumerate(bwt_data):
        ranks[i] = counts[b]
        counts[b] += 1
    starts = [0] * 256
    total = 0
    for b in range(256):
        starts[b] = total
        total += counts[b]
    # LF: из строки в последнем столбце переходим к соответствующей строке первого столбца.
    lf = [starts[bwt_data[i]] + ranks[i] for i in range(n)]
    result = bytearray(n)
    row = original_row
    for pos in range(n - 1, -1, -1):
        result[pos] = bwt_data[row]
        row = lf[row]
    return bytes(result)


# старое имя без row оставлено только для совместимости, но row нужен для корректности
def bwt_inverse(bwt_data: bytes) -> bytes:
    return bwt_inverse_with_row(bwt_data, 0)


def build_suffix_array(data: bytes) -> List[int]:
    return sorted(range(len(data)), key=lambda i: data[i:])


def suffix_array_to_bwt(text: bytes, suffix_array: Sequence[int]) -> bytes:
    n = len(text)
    if len(suffix_array) != n:
        raise ValueError("suffix_array length mismatch")
    return bytes(text[(idx - 1) % n] for idx in suffix_array) if n else b""


def cyclic_suffix_array(data: bytes) -> List[int]:
    n = len(data)
    return sorted(range(n), key=lambda i: data[i:] + data[:i])


def bwt_from_suffix_array(text: bytes) -> Tuple[bytes, int]:
    """BWT на циклическом суффиксном массиве. Для учебной корректности без терминатора."""
    if not text:
        return b"", 0
    sa = cyclic_suffix_array(text)
    bwt = suffix_array_to_bwt(text, sa)
    return bwt, sa.index(0)


BWT_MAGIC = b"BWT1"
BWT_HEADER_FORMAT = ">4sI I"  # magic, block_size, block_count
BWT_HEADER_SIZE = struct.calcsize(BWT_HEADER_FORMAT)
BWT_BLOCK_HEADER_FORMAT = ">II"
BWT_BLOCK_HEADER_SIZE = struct.calcsize(BWT_BLOCK_HEADER_FORMAT)


def bwt_encode_blocks(data: bytes, block_size: int = 4096) -> bytes:
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    blocks = [data[i:i + block_size] for i in range(0, len(data), block_size)]
    out = bytearray(struct.pack(BWT_HEADER_FORMAT, BWT_MAGIC, block_size, len(blocks)))
    for block in blocks:
        transformed, row = bwt_direct(block)
        out += struct.pack(BWT_BLOCK_HEADER_FORMAT, len(block), row)
        out += transformed
    return bytes(out)


def bwt_decode_blocks(encoded: bytes) -> bytes:
    if len(encoded) < BWT_HEADER_SIZE:
        raise ValueError("BWT data is too short")
    magic, block_size, block_count = struct.unpack(BWT_HEADER_FORMAT, encoded[:BWT_HEADER_SIZE])
    if magic != BWT_MAGIC:
        raise ValueError("invalid BWT data")
    pos = BWT_HEADER_SIZE
    out = bytearray()
    for _ in range(block_count):
        if pos + BWT_BLOCK_HEADER_SIZE > len(encoded):
            raise ValueError("truncated BWT block header")
        size, row = struct.unpack(BWT_BLOCK_HEADER_FORMAT, encoded[pos:pos + BWT_BLOCK_HEADER_SIZE])
        pos += BWT_BLOCK_HEADER_SIZE
        block = encoded[pos:pos + size]
        if len(block) != size:
            raise ValueError("truncated BWT block")
        pos += size
        out += bwt_inverse_with_row(block, row)
    if pos != len(encoded):
        raise ValueError("extra bytes after BWT blocks")
    return bytes(out)


# ============================================================
# LZ77 / LZSS / LZ78 / LZW
# ============================================================


def lz77_encode(data: bytes, window_size: int = 4096, look_ahead: int = 32) -> List[Tuple[int, int, Optional[int]]]:
    result: List[Tuple[int, int, Optional[int]]] = []
    i, n = 0, len(data)
    while i < n:
        best_offset, best_length = 0, 0
        for offset in range(1, min(window_size, i) + 1):
            length = 0
            while (length < look_ahead and i + length < n and
                   data[i - offset + length] == data[i + length]):
                length += 1
            if length > best_length:
                best_offset, best_length = offset, length
        if best_length == 0:
            result.append((0, 0, data[i]))
            i += 1
        else:
            next_char = data[i + best_length] if i + best_length < n else None
            result.append((best_offset, best_length, next_char))
            i += best_length + (1 if next_char is not None else 0)
    return result


def lz77_decode(encoded: Sequence[Tuple[int, int, Optional[int]]]) -> bytes:
    out = bytearray()
    for offset, length, next_char in encoded:
        if offset == 0 and length == 0:
            if next_char is None:
                raise ValueError("literal has None char")
            out.append(next_char)
            continue
        if offset <= 0 or offset > len(out):
            raise ValueError("invalid LZ77 offset")
        start = len(out) - offset
        for k in range(length):
            out.append(out[start + k])
        if next_char is not None:
            out.append(next_char)
    return bytes(out)


def _find_longest_match(data: bytes, pos: int, window_size: int, look_ahead: int) -> Tuple[int, int]:
    best_offset, best_length = 0, 0
    for offset in range(1, min(window_size, pos) + 1):
        length = 0
        while (length < look_ahead and pos + length < len(data) and
               data[pos - offset + length] == data[pos + length]):
            length += 1
        if length > best_length:
            best_offset, best_length = offset, length
    return best_offset, best_length


def lzss_encode(data: bytes, window_size: int = 4095, look_ahead: int = 255, min_match: int = 3) -> bytes:
    if not (1 <= window_size <= 65535 and 1 <= look_ahead <= 255):
        raise ValueError("window_size must be <=65535 and look_ahead <=255")
    out = bytearray()
    i = 0
    while i < len(data):
        offset, length = _find_longest_match(data, i, window_size, look_ahead)
        if length >= min_match:
            out.append(1)
            out += struct.pack(">HB", offset, length)
            i += length
        else:
            out.append(0)
            out.append(data[i])
            i += 1
    return bytes(out)


def lzss_decode(encoded: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(encoded):
        flag = encoded[i]
        i += 1
        if flag == 0:
            if i >= len(encoded):
                raise ValueError("truncated LZSS literal")
            out.append(encoded[i])
            i += 1
        elif flag == 1:
            if i + 3 > len(encoded):
                raise ValueError("truncated LZSS reference")
            offset, length = struct.unpack(">HB", encoded[i:i + 3])
            i += 3
            if offset == 0 or offset > len(out):
                raise ValueError("invalid LZSS offset")
            start = len(out) - offset
            for k in range(length):
                out.append(out[start + k])
        else:
            raise ValueError("invalid LZSS flag")
    return bytes(out)


def lz78_encode(data: bytes, max_dict_size: int = 65535) -> List[Tuple[int, Optional[int]]]:
    dictionary = {b"": 0}
    next_code = 1
    result: List[Tuple[int, Optional[int]]] = []
    current = b""
    for byte in data:
        candidate = current + bytes([byte])
        if candidate in dictionary:
            current = candidate
        else:
            result.append((dictionary[current], byte))
            if next_code <= max_dict_size:
                dictionary[candidate] = next_code
                next_code += 1
            current = b""
    if current:
        result.append((dictionary[current], None))
    return result


def lz78_decode(encoded: Sequence[Tuple[int, Optional[int]]], max_dict_size: int = 65535) -> bytes:
    dictionary: Dict[int, bytes] = {0: b""}
    next_code = 1
    out = bytearray()
    for index, char in encoded:
        if index not in dictionary:
            raise ValueError("invalid LZ78 index")
        entry = dictionary[index] + (bytes([char]) if char is not None else b"")
        out += entry
        if char is not None and next_code <= max_dict_size:
            dictionary[next_code] = entry
            next_code += 1
    return bytes(out)


def lz78_pack(pairs: Sequence[Tuple[int, Optional[int]]]) -> bytes:
    out = bytearray()
    for idx, char in pairs:
        out += struct.pack(">I", idx)
        if char is None:
            out.append(0)
            out.append(0)
        else:
            out.append(1)
            out.append(char)
    return bytes(out)


def lz78_unpack(data: bytes) -> List[Tuple[int, Optional[int]]]:
    if len(data) % 6 != 0:
        raise ValueError("invalid packed LZ78 length")
    pairs = []
    for i in range(0, len(data), 6):
        idx = struct.unpack(">I", data[i:i + 4])[0]
        flag = data[i + 4]
        char = data[i + 5]
        pairs.append((idx, char if flag else None))
    return pairs


def lzw_encode(data: bytes, max_dict_size: int = 65535) -> List[int]:
    dictionary = {bytes([i]): i for i in range(256)}
    next_code = 256
    current = b""
    result: List[int] = []
    for byte in data:
        candidate = current + bytes([byte])
        if candidate in dictionary:
            current = candidate
        else:
            result.append(dictionary[current])
            if next_code <= max_dict_size:
                dictionary[candidate] = next_code
                next_code += 1
            current = bytes([byte])
    if current:
        result.append(dictionary[current])
    return result


def lzw_decode(encoded: Sequence[int], max_dict_size: int = 65535) -> bytes:
    if not encoded:
        return b""
    dictionary = {i: bytes([i]) for i in range(256)}
    next_code = 256
    old_code = encoded[0]
    if old_code not in dictionary:
        raise ValueError("invalid first LZW code")
    out = bytearray(dictionary[old_code])
    for code in encoded[1:]:
        if code in dictionary:
            entry = dictionary[code]
        elif code == next_code:
            entry = dictionary[old_code] + dictionary[old_code][:1]
        else:
            raise ValueError("invalid LZW code")
        out += entry
        if next_code <= max_dict_size:
            dictionary[next_code] = dictionary[old_code] + entry[:1]
            next_code += 1
        old_code = code
    return bytes(out)


def lzw_pack(codes: Sequence[int]) -> bytes:
    out = bytearray()
    for code in codes:
        out += struct.pack(">H", code)
    return bytes(out)


def lzw_unpack(data: bytes) -> List[int]:
    if len(data) % 2 != 0:
        raise ValueError("invalid packed LZW length")
    return [struct.unpack(">H", data[i:i + 2])[0] for i in range(0, len(data), 2)]


# ============================================================
# Компрессоры из финального списка задания
# ============================================================


def compressor_ha_encode(data: bytes) -> bytes:
    payload, meta = huffman_encode(data)
    lengths: Dict[int, int] = meta["lengths"]  # type: ignore[assignment]
    out = bytearray(struct.pack(HA_HEADER_FORMAT, HA_MAGIC, int(meta["original_size"]), len(lengths)))
    out += struct.pack(">Q", int(meta["bit_length"]))
    for symbol, length in sorted(lengths.items()):
        out += struct.pack(">BB", symbol, length)
    out += payload
    return bytes(out)


def compressor_ha_decode(encoded: bytes) -> bytes:
    temp = Path("__temp_ha_decode.bin")
    # без файлов: парсим тот же контейнер напрямую
    if len(encoded) < HA_HEADER_SIZE + 8:
        raise ValueError("HA data too short")
    magic, original_size, count = struct.unpack(HA_HEADER_FORMAT, encoded[:HA_HEADER_SIZE])
    if magic != HA_MAGIC:
        raise ValueError("invalid HA data")
    bit_length = struct.unpack(">Q", encoded[HA_HEADER_SIZE:HA_HEADER_SIZE + 8])[0]
    pos = HA_HEADER_SIZE + 8
    lengths = {}
    for _ in range(count):
        symbol, length = struct.unpack(">BB", encoded[pos:pos + 2])
        lengths[symbol] = length
        pos += 2
    return huffman_decode(encoded[pos:], {"lengths": lengths, "original_size": original_size, "bit_length": bit_length})


def compressor_rle_encode(data: bytes, ms: int = 1, mc: int = 1) -> bytes:
    return struct.pack(RLE_HEADER_FORMAT, RLE_MAGIC, ms, mc, len(data)) + rle_encode(data, ms, mc)


def compressor_rle_decode(encoded: bytes) -> bytes:
    magic, ms, mc, original_size = struct.unpack(RLE_HEADER_FORMAT, encoded[:RLE_HEADER_SIZE])
    if magic != RLE_MAGIC:
        raise ValueError("invalid RLE compressor data")
    out = rle_decode(encoded[RLE_HEADER_SIZE:], ms, mc)
    if len(out) != original_size:
        raise ValueError("RLE original size mismatch")
    return out


def compressor_bwt_rle_encode(data: bytes, block_size: int = 1024, ms: int = 1, mc: int = 1) -> bytes:
    return compressor_rle_encode(bwt_encode_blocks(data, block_size), ms, mc)


def compressor_bwt_rle_decode(encoded: bytes) -> bytes:
    return bwt_decode_blocks(compressor_rle_decode(encoded))


def compressor_bwt_mtf_ha_encode(data: bytes, block_size: int = 1024) -> bytes:
    return compressor_ha_encode(mtf_encode(bwt_encode_blocks(data, block_size)))


def compressor_bwt_mtf_ha_decode(encoded: bytes) -> bytes:
    return bwt_decode_blocks(mtf_decode(compressor_ha_decode(encoded)))


def compressor_bwt_mtf_rle_ha_encode(data: bytes, block_size: int = 1024, ms: int = 1, mc: int = 1) -> bytes:
    stage = mtf_encode(bwt_encode_blocks(data, block_size))
    stage = compressor_rle_encode(stage, ms, mc)
    return compressor_ha_encode(stage)


def compressor_bwt_mtf_rle_ha_decode(encoded: bytes) -> bytes:
    stage = compressor_ha_decode(encoded)
    stage = compressor_rle_decode(stage)
    return bwt_decode_blocks(mtf_decode(stage))


LZSS_MAGIC = b"LZS1"
LZSS_HEADER_FORMAT = ">4sQHHB"
LZSS_HEADER_SIZE = struct.calcsize(LZSS_HEADER_FORMAT)


def compressor_lzss_encode(data: bytes, window_size: int = 4095, look_ahead: int = 255, min_match: int = 3) -> bytes:
    payload = lzss_encode(data, window_size, look_ahead, min_match)
    header = struct.pack(LZSS_HEADER_FORMAT, LZSS_MAGIC, len(data), window_size, look_ahead, min_match)
    return header + payload


def compressor_lzss_decode(encoded: bytes) -> bytes:
    if len(encoded) < LZSS_HEADER_SIZE:
        raise ValueError("LZSS data too short")
    magic, original_size, window_size, look_ahead, min_match = struct.unpack(LZSS_HEADER_FORMAT, encoded[:LZSS_HEADER_SIZE])
    if magic != LZSS_MAGIC:
        raise ValueError("invalid LZSS data")
    out = lzss_decode(encoded[LZSS_HEADER_SIZE:])
    if len(out) != original_size:
        raise ValueError("LZSS original size mismatch")
    return out


def compressor_lzss_ha_encode(data: bytes, window_size: int = 4095) -> bytes:
    return compressor_ha_encode(compressor_lzss_encode(data, window_size=window_size))


def compressor_lzss_ha_decode(encoded: bytes) -> bytes:
    return compressor_lzss_decode(compressor_ha_decode(encoded))


LZW_MAGIC = b"LZW1"
LZW_HEADER_FORMAT = ">4sQI"
LZW_HEADER_SIZE = struct.calcsize(LZW_HEADER_FORMAT)


def compressor_lzw_encode(data: bytes, max_dict_size: int = 65535) -> bytes:
    codes = lzw_encode(data, max_dict_size)
    payload = lzw_pack(codes)
    return struct.pack(LZW_HEADER_FORMAT, LZW_MAGIC, len(data), max_dict_size) + payload


def compressor_lzw_decode(encoded: bytes) -> bytes:
    if len(encoded) < LZW_HEADER_SIZE:
        raise ValueError("LZW data too short")
    magic, original_size, max_dict_size = struct.unpack(LZW_HEADER_FORMAT, encoded[:LZW_HEADER_SIZE])
    if magic != LZW_MAGIC:
        raise ValueError("invalid LZW data")
    out = lzw_decode(lzw_unpack(encoded[LZW_HEADER_SIZE:]), max_dict_size)
    if len(out) != original_size:
        raise ValueError("LZW original size mismatch")
    return out


def compressor_lzw_ha_encode(data: bytes, max_dict_size: int = 65535) -> bytes:
    return compressor_ha_encode(compressor_lzw_encode(data, max_dict_size=max_dict_size))


def compressor_lzw_ha_decode(encoded: bytes) -> bytes:
    return compressor_lzw_decode(compressor_ha_decode(encoded))


COMPRESSORS = {
    "HA": (compressor_ha_encode, compressor_ha_decode),
    "RLE": (compressor_rle_encode, compressor_rle_decode),
    "BWT+RLE": (compressor_bwt_rle_encode, compressor_bwt_rle_decode),
    "BWT+MTF+HA": (compressor_bwt_mtf_ha_encode, compressor_bwt_mtf_ha_decode),
    "BWT+MTF+RLE+HA": (compressor_bwt_mtf_rle_ha_encode, compressor_bwt_mtf_rle_ha_decode),
    "LZSS": (compressor_lzss_encode, compressor_lzss_decode),
    "LZSS+HA": (compressor_lzss_ha_encode, compressor_lzss_ha_decode),
    "LZW": (compressor_lzw_encode, compressor_lzw_decode),
    "LZW+HA": (compressor_lzw_ha_encode, compressor_lzw_ha_decode),
}


# ============================================================
# Эксперименты, таблицы, графики
# ============================================================


def analyze_rle_estimate(data: bytes, ms: int = 1, mc: int = 1) -> Dict[str, float]:
    encoded = rle_encode(data, ms, mc)
    return {
        "original_size": len(data),
        "encoded_size_without_header": len(encoded),
        "ratio": compression_ratio(len(data), len(encoded)),
    }


def analyze_file(filename: str | os.PathLike, ms: int = 1, mc: int = 1) -> float:
    """Простой анализ RLE для одного файла."""
    data = Path(filename).read_bytes()
    encoded = rle_encode(data, ms, mc)

    original_size = len(data)
    encoded_size = len(encoded)
    k = compression_ratio(original_size, encoded_size)

    print("Файл:", filename)
    print("ms =", ms, "mc =", mc)
    print("Исходный размер:", original_size, "байт")
    print("Размер после RLE без заголовка:", encoded_size, "байт")
    print("Коэффициент сжатия:", round(k, 4))
    print()

    return k


def check_file(input_name: str | os.PathLike, ms: int = 1, mc: int = 1) -> bool:
    """
    Проверка полного цикла:
    файл -> RLE -> файл .rle -> обратно -> файл .decoded.
    """
    input_path = Path(input_name)
    compressed_name = str(input_path) + ".rle"
    decoded_name = str(input_path) + ".decoded"

    write_rle_file(input_path, compressed_name, ms, mc)
    decode_rle_file(compressed_name, decoded_name)

    original = input_path.read_bytes()
    decoded = Path(decoded_name).read_bytes()

    if original == decoded:
        print("OK:", input_name)
        return True

    print("ERROR:", input_name)
    return False


def analyze_many_files(files: Sequence[Tuple[str, int, int]]) -> None:
    """Печатает маленькую таблицу по нескольким файлам."""
    print("%-35s %12s %12s %10s" % ("Файл", "Исходный", "RLE", "K"))
    for filename, ms, mc in files:
        data = Path(filename).read_bytes()
        encoded = rle_encode(data, ms, mc)
        original_size = len(data)
        encoded_size = len(encoded)
        k = compression_ratio(original_size, encoded_size)
        print("%-35s %12d %12d %10.4f" %
              (os.path.basename(filename), original_size, encoded_size, k))


def safe_call(func, *args) -> None:
    """
    Чтобы программа не падала, если какого-то файла пока нет.
    """
    try:
        func(*args)
    except FileNotFoundError as e:
        print("Файл не найден:", e.filename)
    except Exception as e:
        print("Ошибка:", e)


def run_compressor_on_data(data: bytes, name: str) -> Dict[str, float | str | int]:
    enc, dec = COMPRESSORS[name]
    t0 = time.perf_counter()
    compressed = enc(data)
    t1 = time.perf_counter()
    restored = dec(compressed)
    t2 = time.perf_counter()
    if restored != data:
        raise AssertionError(f"{name} failed roundtrip")
    return {
        "compressor": name,
        "original_size": len(data),
        "compressed_size": len(compressed),
        "decompressed_size": len(restored),
        "compression_ratio": compression_ratio(len(data), len(compressed)),
        "encode_seconds": t1 - t0,
        "decode_seconds": t2 - t1,
    }


def run_all_compressors_for_files(files: Sequence[str | os.PathLike], csv_path: Optional[str | os.PathLike] = None) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for file in files:
        data = Path(file).read_bytes()
        for name in COMPRESSORS:
            row = run_compressor_on_data(data, name)
            row["file"] = os.path.basename(file)
            rows.append(row)
    if csv_path:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(rows)
    return rows


def experiment_bwt_mtf_entropy(data: bytes, block_sizes: Sequence[int]) -> List[Dict[str, float | int]]:
    original_entropy = calculate_entropy(data, 1) if data else 0.0
    rows = []
    for block_size in block_sizes:
        transformed = mtf_encode(bwt_encode_blocks(data, block_size))
        rows.append({
            "block_size": block_size,
            "original_entropy": original_entropy,
            "bwt_mtf_entropy": calculate_entropy(transformed, 1) if transformed else 0.0,
        })
    return rows


def experiment_lzss_window(data: bytes, window_sizes: Sequence[int]) -> List[Dict[str, float | int]]:
    rows = []
    for w in window_sizes:
        t0 = time.perf_counter()
        encoded = compressor_lzss_encode(data, window_size=w)
        t1 = time.perf_counter()
        if compressor_lzss_decode(encoded) != data:
            raise AssertionError("LZSS experiment roundtrip failed")
        rows.append({
            "window_size": w,
            "compressed_size": len(encoded),
            "compression_ratio": compression_ratio(len(data), len(encoded)),
            "seconds": t1 - t0,
        })
    return rows


def experiment_lzw_dict(data: bytes, dict_sizes: Sequence[int]) -> List[Dict[str, float | int]]:
    rows = []
    for d in dict_sizes:
        t0 = time.perf_counter()
        encoded = compressor_lzw_encode(data, max_dict_size=d)
        t1 = time.perf_counter()
        if compressor_lzw_decode(encoded) != data:
            raise AssertionError("LZW experiment roundtrip failed")
        rows.append({
            "dict_size": d,
            "compressed_size": len(encoded),
            "compression_ratio": compression_ratio(len(data), len(encoded)),
            "seconds": t1 - t0,
        })
    return rows


def save_experiment_csv(rows: Sequence[Dict[str, object]], csv_path: str | os.PathLike) -> None:
    if not rows:
        return
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_experiment(rows: Sequence[Dict[str, object]], x_key: str, y_key: str, output_png: str | os.PathLike,
                    title: str = "Experiment", xlabel: Optional[str] = None, ylabel: Optional[str] = None) -> None:
    import matplotlib.pyplot as plt
    xs = [row[x_key] for row in rows]
    ys = [row[y_key] for row in rows]
    plt.figure()
    plt.plot(xs, ys, marker="o", label=y_key)
    plt.title(title)
    plt.xlabel(xlabel or x_key)
    plt.ylabel(ylabel or y_key)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_png)
    plt.close()


# ============================================================
# Самопроверка
# ============================================================


def run_tests(verbose: bool = True) -> bool:
    samples = [
        b"",
        b"AAAAAA",
        bytes([0xCF] * 5),
        bytes([0xCF, 0xCE, 0xCF, 0xCE, 0xCF]),
        bytes([0xCF, 0xCE, 0xCF, 0xCE, 0xCF, 0xCF, 0xCF, 0xCF, 0xCF, 0xCF]),
        "Привет, привет, привет!".encode("utf-8"),
        b"banana",
        b"banana banana banana ABABABABAB",
        bytes(range(256)),
    ]
    random.seed(1)
    for _ in range(5):
        samples.append(bytes(random.randrange(0, 256) for _ in range(300)))

    # Bit strings
    bit_test = "101010001111000101"
    writer = BitWriter(); writer.write_bits(bit_test)
    payload, bit_len = writer.to_bytes()
    assert BitReader(payload, bit_len).read_bits(bit_len) == bit_test

    # RLE
    assert rle_encode(bytes([0xCF] * 5), 1, 1) == bytes([0x05, 0xCF])
    assert rle_encode(bytes([0xCF, 0xCE, 0xCF, 0xCE, 0xCF]), 1, 1) == bytes([0x85, 0xCF, 0xCE, 0xCF, 0xCE, 0xCF])
    for s in samples:
        assert rle_decode(rle_encode(s, 1, 1), 1, 1) == s
    assert rle_decode(rle_encode(bytes([0xCF, 0xCE]) * 3, 2, 1), 2, 1) == bytes([0xCF, 0xCE]) * 3

    # UTF-32 text RLE
    text = "Привет Привет"
    assert decode_text_from_utf32(encode_text_as_utf32(text)) == text

    # Entropy
    assert calculate_entropy(b"AAAA", 1) == 0.0

    # MTF
    for s in samples:
        assert mtf_decode(mtf_encode(s)) == s

    # Huffman
    for s in samples:
        enc, meta = huffman_encode(s)
        assert huffman_decode(enc, meta) == s
        model = probability_model_from_data(s)
        if model:
            enc2, meta2 = huffman_encode(s, model)
            assert huffman_decode(enc2, meta2) == s

    # BWT
    bwt_banana, row = bwt_direct(b"banana")
    assert bwt_inverse_naive(bwt_banana, row) == b"banana"
    assert bwt_inverse_with_row(bwt_banana, row) == b"banana"
    for s in samples:
        if len(s) <= 400:
            b, r = bwt_direct(s)
            assert bwt_inverse_with_row(b, r) == s
            assert bwt_decode_blocks(bwt_encode_blocks(s, 64)) == s

    # SA -> BWT
    s = b"banana"
    csa = cyclic_suffix_array(s)
    assert suffix_array_to_bwt(s, csa) == bwt_direct(s)[0]

    # LZ family
    for s in samples:
        assert lz77_decode(lz77_encode(s, 64, 16)) == s
        assert lzss_decode(lzss_encode(s, 128, 32)) == s
        assert lz78_decode(lz78_encode(s)) == s
        assert lzw_decode(lzw_encode(s)) == s

    # Compressors: use smaller nonempty data to keep BWT fast
    compressor_samples = [b"banana banana banana ABABABABAB" * 2, b"AAAAABBBBBCCCCCDDDDDEEEEE", bytes(range(64)) * 2]
    for s in compressor_samples:
        for name, (enc, dec) in COMPRESSORS.items():
            restored = dec(enc(s))
            assert restored == s, name

    # Arithmetic experiment function
    arithmetic_encode_double(b"banana")
    arithmetic_double_collision_length(b"banana" * 10)

    if verbose:
        print("Все самотесты пройдены успешно")
    return True


def show_examples() -> None:
    examples = [
        (bytes([0xCF] * 5), 1, 1),
        (bytes([0xCF, 0xCE, 0xCF, 0xCE, 0xCF]), 1, 1),
        (bytes([0xCF, 0xCE, 0xCF, 0xCE, 0xCF, 0xCF, 0xCF, 0xCF, 0xCF, 0xCF]), 1, 1),
        (bytes([0xCF, 0xCE]) * 3, 2, 1),
        (bytes([0xCF, 0xCE, 0xCF]) * 2, 3, 1),
    ]
    for data, ms, mc in examples:
        encoded = rle_encode(data, ms, mc)
        print(f"ms={ms} mc={mc}: {print_hex(data)} -> {print_hex(encoded)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compression lab toolkit")
    parser.add_argument("--test", action="store_true", help="run self-tests")
    parser.add_argument("--examples", action="store_true", help="show RLE examples")
    parser.add_argument("--compress", nargs=3, metavar=("COMPRESSOR", "INPUT", "OUTPUT"), help="compress file")
    parser.add_argument("--decompress", nargs=3, metavar=("COMPRESSOR", "INPUT", "OUTPUT"), help="decompress file")
    args = parser.parse_args()

    if args.test:
        run_tests()
    if args.examples:
        show_examples()
    if args.compress:
        name, inp, out = args.compress
        if name not in COMPRESSORS:
            raise SystemExit(f"unknown compressor: {name}")
        data = Path(inp).read_bytes()
        Path(out).write_bytes(COMPRESSORS[name][0](data))
    if args.decompress:
        name, inp, out = args.decompress
        if name not in COMPRESSORS:
            raise SystemExit(f"unknown compressor: {name}")
        data = Path(inp).read_bytes()
        Path(out).write_bytes(COMPRESSORS[name][1](data))


# Запуск программы
if __name__ == "__main__":
    main()

    safe_call(make_enwik7, "data/enwik9", "data/enwik7")
    safe_call(analyze_file, "data/enwik7", 1, 1)
    safe_call(analyze_file, "data/text.txt", 1, 1)
    safe_call(analyze_file, "data/binary.bin", 1, 1)

    # Перевод изображений в raw.
    safe_call(image_to_raw, "data/bw.jpeg", "data/bw.raw", RAW_BW)
    safe_call(image_to_raw, "data/grayscale.png", "data/grayscale.raw", RAW_GRAY)
    safe_call(image_to_raw, "data/color.png", "data/color.raw", RAW_RGB)

    # Анализ raw-файлов:
    safe_call(analyze_file, "data/bw.raw", 1, 1)
    safe_call(analyze_file, "data/grayscale.raw", 1, 1)
    safe_call(analyze_file, "data/color.raw", 1, 1)

    # Проверка, что RLE правильно сжимает и восстанавливает файлы:
    safe_call(check_file, "data/bw.raw", 1, 1)
    safe_call(check_file, "data/grayscale.raw", 1, 1)
    safe_call(check_file, "data/color.raw", 1, 1)
