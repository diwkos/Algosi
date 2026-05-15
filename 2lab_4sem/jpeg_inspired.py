from PIL import Image
import os
import math


def save_raw_with_meta(img, output_file, color_space=None):
    if img.mode not in ['RGB', 'L', '1']:
        img = img.convert('RGB')

    if img.mode == '1':
        img_type = 'bw'
        bytes_per_pixel = 1
        if color_space is None:
            color_space = 'BW'
    elif img.mode == 'L':
        img_type = 'grayscale'
        bytes_per_pixel = 1
        if color_space is None:
            color_space = 'GRAY'
    else:
        img_type = 'color'
        bytes_per_pixel = 3
        if color_space is None:
            color_space = 'RGB'

    meta_file = output_file + '.meta'
    with open(meta_file, 'w', encoding='utf-8') as f:
        f.write(f'type={img_type}\n')
        f.write(f'color_space={color_space}\n')
        f.write(f'width={img.width}\n')
        f.write(f'height={img.height}\n')
        f.write(f'bytes_per_pixel={bytes_per_pixel}\n')

    with open(output_file, 'wb') as f:
        if img.mode == 'RGB':
            for pixel in img.getdata():
                f.write(bytes(pixel))
        else:
            for pixel in img.getdata():
                if img.mode == '1':
                    if pixel != 0:
                        pixel = 255
                f.write(bytes([pixel]))

    return {
        'type': img_type,
        'width': img.width,
        'height': img.height,
        'bytes_per_pixel': bytes_per_pixel,
        'color_space': color_space
    }


def convert_to_raw(input_file, output_file):
    img = Image.open(input_file)
    original_file_size = os.path.getsize(input_file)

    raw_info = save_raw_with_meta(img, output_file)

    return {
        'original_size': original_file_size,
        'raw_type': raw_info['type'],
        'width': raw_info['width'],
        'height': raw_info['height'],
        'bytes_per_pixel': raw_info['bytes_per_pixel']
    }


def calculate_koeff(info):
    raw_size = info['width'] * info['height'] * info['bytes_per_pixel']
    original_size = info['original_size']

    if original_size > 0:
        koeff = raw_size / original_size
        print(f'Размер исходного файла: {original_size} байт')
        print(f'Размер raw-файла (без meta): {raw_size} байт')
        print(f'Коэффициент: {koeff:.2f}')
    else:
        print('Нельзя посчитать коэффициент')

def rgb_to_ycbcr(img):
    img = img.convert('RGB')
    pixels = list(img.getdata())

    new_pixels = []

    for (r, g, b) in pixels:
        y = 0.299 * r + 0.587 * g + 0.114 * b
        cb = -0.1687 * r - 0.3313 * g + 0.5 * b + 128
        cr = 0.5 * r - 0.4187 * g - 0.0813 * b + 128

        # округляем и ограничиваем 0..255
        y = int(min(max(round(y), 0), 255))
        cb = int(min(max(round(cb), 0), 255))
        cr = int(min(max(round(cr), 0), 255))

        new_pixels.append((y, cb, cr))

    new_img = Image.new('RGB', img.size)
    new_img.putdata(new_pixels)

    return new_img

def ycbcr_to_rgb(img):
    pixels = list(img.getdata())

    new_pixels = []

    for (y, cb, cr) in pixels:
        r = y + 1.402 * (cr - 128)
        g = y - 0.344136 * (cb - 128) - 0.714136 * (cr - 128)
        b = y + 1.772 * (cb - 128)

        r = int(min(max(round(r), 0), 255))
        g = int(min(max(round(g), 0), 255))
        b = int(min(max(round(b), 0), 255))

        new_pixels.append((r, g, b))

    new_img = Image.new('RGB', img.size)
    new_img.putdata(new_pixels)

    return new_img

def downsample(img, k):
    img = img.convert('RGB')
    width, height = img.size

    new_width = width // k
    new_height = height // k

    new_img = Image.new('RGB', (new_width, new_height))

    for y in range(new_height):
        for x in range(new_width):
            pixel = img.getpixel((x * k, y * k))
            new_img.putpixel((x, y), pixel)

    return new_img


def upsample(img, k):
    img = img.convert('RGB')
    width, height = img.size

    new_width = width * k
    new_height = height * k

    new_img = Image.new('RGB', (new_width, new_height))

    for y in range(height):
        for x in range(width):
            pixel = img.getpixel((x, y))

            for dy in range(k):
                for dx in range(k):
                    new_img.putpixel((x * k + dx, y * k + dy), pixel)

    return new_img

# ====================================================================
# ====================================================================
# Блок интерполяций

def linear_interpolation(x1, x2, y1, y2, x):
    if x2 == x1:
        return y1
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1) # Находим y для "следующей" точки с x координатой


def linear_spline(xs, ys, x):
    n = len(xs)

    if n != len(ys):
        raise ValueError('xs и ys должны быть одной длины')

    if x <= xs[0]:
        return ys[0]

    if x >= xs[n - 1]:
        return ys[n - 1]

    for i in range(n - 1):
        if xs[i] <= x <= xs[i + 1]:
            return linear_interpolation(xs[i], xs[i + 1], ys[i], ys[i + 1], x)

    return None


def bilinear_interpolation(x1, x2, y1, y2, z11, z12, z21, z22, x, y):
    r1 = linear_interpolation(x1, x2, z11, z21, x)
    r2 = linear_interpolation(x1, x2, z12, z22, x)
    return linear_interpolation(y1, y2, r1, r2, y)

def get_interpolation_nodes(old_size, new_index, new_size):
    if new_size <= 0:
        raise ValueError('Размер получившегося изображения должен быть положительным')

    if old_size <= 0:
        raise ValueError('Размер исходного изображения должен быть положительным')

    if new_size == 1:
        coord = 0.0
    else:
        coord = new_index * (old_size - 1) / (new_size - 1)

    left = int(math.floor(coord))
    right = min(left + 1, old_size - 1)

    return coord, left, right


def resize_bilinear(img, new_width, new_height):# сын маминой подруги в отличае от upsample
    img = img.convert('RGB')
    width, height = img.size

    if new_width <= 0 or new_height <= 0:
        raise ValueError('Размеры выходного изображения должны быть положительными')

    new_img = Image.new('RGB', (new_width, new_height))# создаем новое изображение

    for new_y in range(new_height):
        y, y1, y2 = get_interpolation_nodes(height, new_y, new_height)

        for new_x in range(new_width):
            x, x1, x2 = get_interpolation_nodes(width, new_x, new_width)

            p11 = img.getpixel((x1, y1))
            p12 = img.getpixel((x1, y2))
            p21 = img.getpixel((x2, y1))
            p22 = img.getpixel((x2, y2))

            r = bilinear_interpolation(x1, x2, y1, y2, p11[0], p12[0], p21[0], p22[0], x, y)
            g = bilinear_interpolation(x1, x2, y1, y2, p11[1], p12[1], p21[1], p22[1], x, y)
            b = bilinear_interpolation(x1, x2, y1, y2, p11[2], p12[2], p21[2], p22[2], x, y)

            r = int(min(max(round(r), 0), 255))
            g = int(min(max(round(g), 0), 255))
            b = int(min(max(round(b), 0), 255))

            new_img.putpixel((new_x, new_y), (r, g, b))

    return new_img


# ====================================================================
# ====================================================================
# Блок ДКП

def alpha(index, size):
    if index == 0:
        return math.sqrt(1 / size)
    return math.sqrt(2 / size)


def image_to_matrix(img):
    img = img.convert('L')
    width, height = img.size
    matrix = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append(img.getpixel((x, y)))
        matrix.append(row)
    return matrix


def matrix_to_image(matrix):
    height = len(matrix)
    width = len(matrix[0])
    img = Image.new('L', (width, height))
    for y in range(height):
        for x in range(width):
            value = int(round(matrix[y][x]))
            value = min(max(value, 0), 255)
            img.putpixel((x, y), value)
    return img


def level_shift_block(block):
    return [[float(value) - 128.0 for value in row] for row in block]


def inverse_level_shift_block(block):
    return [[float(value) + 128.0 for value in row] for row in block]


def split_into_blocks(matrix, block_h=8, block_w=8, pad=True):
    height = len(matrix)
    width = len(matrix[0])
    padded_height = height
    padded_width = width

    if pad:
        if height % block_h != 0:
            padded_height = height + (block_h - height % block_h)
        if width % block_w != 0:
            padded_width = width + (block_w - width % block_w)

    padded = [[0.0 for _ in range(padded_width)] for _ in range(padded_height)]
    for y in range(height):
        for x in range(width):
            padded[y][x] = float(matrix[y][x])

    blocks = []
    for by in range(0, padded_height, block_h):
        row_blocks = []
        for bx in range(0, padded_width, block_w):
            block = []
            for y in range(block_h):
                row = []
                for x in range(block_w):
                    row.append(padded[by + y][bx + x])
                block.append(row)
            row_blocks.append(block)
        blocks.append(row_blocks)

    return blocks, height, width, padded_height, padded_width


def merge_blocks(blocks, original_h, original_w, block_h=8, block_w=8):
    padded_height = len(blocks) * block_h
    padded_width = len(blocks[0]) * block_w
    matrix = [[0.0 for _ in range(padded_width)] for _ in range(padded_height)]

    for block_row_index, block_row in enumerate(blocks):
        for block_col_index, block in enumerate(block_row):
            base_y = block_row_index * block_h
            base_x = block_col_index * block_w
            for y in range(block_h):
                for x in range(block_w):
                    matrix[base_y + y][base_x + x] = block[y][x]

    cropped = []
    for y in range(original_h):
        cropped.append(matrix[y][:original_w])
    return cropped


def dct(block):
    n = len(block)
    m = len(block[0])
    coeffs = [[0.0 for _ in range(m)] for _ in range(n)]

    for u in range(n):
        for v in range(m):
            total = 0.0
            for x in range(n):
                for y in range(m):
                    total += (
                        block[x][y]
                        * math.cos((2 * x + 1) * u * math.pi / (2 * n))
                        * math.cos((2 * y + 1) * v * math.pi / (2 * m))
                    )
            coeffs[u][v] = alpha(u, n) * alpha(v, m) * total
    return coeffs


def idct(coeffs):
    n = len(coeffs)
    m = len(coeffs[0])
    block = [[0.0 for _ in range(m)] for _ in range(n)]

    for x in range(n):
        for y in range(m):
            total = 0.0
            for u in range(n):
                for v in range(m):
                    total += (
                        alpha(u, n)
                        * alpha(v, m)
                        * coeffs[u][v]
                        * math.cos((2 * x + 1) * u * math.pi / (2 * n))
                        * math.cos((2 * y + 1) * v * math.pi / (2 * m))
                    )
            block[x][y] = total
    return block


def make_dct_matrix(size):
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    for u in range(size):
        for x in range(size):
            matrix[u][x] = alpha(u, size) * math.cos((2 * x + 1) * u * math.pi / (2 * size))
    return matrix


def transpose_matrix(matrix):
    rows = len(matrix)
    cols = len(matrix[0])
    return [[matrix[i][j] for i in range(rows)] for j in range(cols)]


def multiply_matrices(a, b):
    rows_a = len(a)
    cols_a = len(a[0])
    rows_b = len(b)
    cols_b = len(b[0])

    if cols_a != rows_b:
        raise ValueError('Нельзя перемножить матрицы: несовместимые размеры')

    result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            total = 0.0
            for k in range(cols_a):
                total += a[i][k] * b[k][j]
            result[i][j] = total
    return result


def dct_matrix(block):
    n = len(block)
    m = len(block[0])
    if n != m:
        raise ValueError('Матричная реализация ниже сделана для квадратных блоков NxN')
    d = make_dct_matrix(n)
    dt = transpose_matrix(d)
    return multiply_matrices(multiply_matrices(d, block), dt)


def idct_matrix(coeffs):
    n = len(coeffs)
    m = len(coeffs[0])
    if n != m:
        raise ValueError('Матричная реализация ниже сделана для квадратных блоков NxN')
    d = make_dct_matrix(n)
    dt = transpose_matrix(d)
    return multiply_matrices(multiply_matrices(dt, coeffs), d)


def quantize_dct(coeffs, q_matrix):
    height = len(coeffs)
    width = len(coeffs[0])
    result = [[0 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if q_matrix[y][x] == 0:
                raise ValueError('В матрице квантования не должно быть нулей')
            result[y][x] = round(coeffs[y][x] / q_matrix[y][x])
    return result


def dequantize_dct(q_coeffs, q_matrix):
    height = len(q_coeffs)
    width = len(q_coeffs[0])
    result = [[0.0 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            result[y][x] = q_coeffs[y][x] * q_matrix[y][x]
    return result


def process_blocks_with_dct(matrix, block_h=8, block_w=8, q_matrix=None, use_matrix_method=False):
    blocks, original_h, original_w, _, _ = split_into_blocks(matrix, block_h, block_w, pad=True)
    restored_blocks = []

    for block_row in blocks:
        restored_row = []
        for block in block_row:
            shifted = level_shift_block(block)
            if use_matrix_method:
                coeffs = dct_matrix(shifted)
            else:
                coeffs = dct(shifted)

            if q_matrix is not None:
                quantized = quantize_dct(coeffs, q_matrix)
                coeffs_for_restore = dequantize_dct(quantized, q_matrix)
            else:
                coeffs_for_restore = coeffs

            if use_matrix_method:
                restored = idct_matrix(coeffs_for_restore)
            else:
                restored = idct(coeffs_for_restore)

            restored_row.append(inverse_level_shift_block(restored))
        restored_blocks.append(restored_row)

    return merge_blocks(restored_blocks, original_h, original_w, block_h, block_w)


def max_abs_difference_matrix(a, b):
    height = len(a)
    width = len(a[0])
    diff = 0.0
    for y in range(height):
        for x in range(width):
            diff = max(diff, abs(a[y][x] - b[y][x]))
    return diff


def print_matrix(matrix, digits=2):
    for row in matrix:
        print(' '.join(f'{value:.{digits}f}' if isinstance(value, float) else str(value) for value in row))


def get_standard_quantization_matrix():
    return [
        [16, 11, 10, 16, 24, 40, 51, 61],
        [12, 12, 14, 19, 26, 58, 60, 55],
        [14, 13, 16, 24, 40, 57, 69, 56],
        [14, 17, 22, 29, 51, 87, 80, 62],
        [18, 22, 37, 56, 68, 109, 103, 77],
        [24, 35, 55, 64, 81, 104, 113, 92],
        [49, 64, 78, 87, 103, 121, 120, 101],
        [72, 92, 95, 98, 112, 100, 103, 99],
    ]


def compare_images(img1, img2):
    img1 = img1.convert('RGB')
    img2 = img2.convert('RGB')

    if img1.size != img2.size:
        print('Изображения разного размера, сравнение невозможно')
        return

    width, height = img1.size
    total = 0

    for y in range(height):
        for x in range(width):
            p1 = img1.getpixel((x, y))
            p2 = img2.getpixel((x, y))

            total += abs(p1[0] - p2[0])
            total += abs(p1[1] - p2[1])
            total += abs(p1[2] - p2[2])

    avg = total / (width * height * 3)
    print(f'Среднее отличие по каналам: {avg:.4f}')



# ====================================================================
# ====================================================================
# Блок JPEG-подобного энтропийного кодирования

import json
import struct


def zigzag_indices(rows, cols):
    indices = []
    for s in range(rows + cols - 1):
        diagonal = []
        row_start = max(0, s - (cols - 1))
        row_end = min(rows - 1, s)
        for r in range(row_start, row_end + 1):
            c = s - r
            diagonal.append((r, c))

        if s % 2 == 0:
            diagonal.reverse()

        indices.extend(diagonal)
    return indices


def zigzag_scan(matrix):
    rows = len(matrix)
    cols = len(matrix[0])
    return [matrix[r][c] for r, c in zigzag_indices(rows, cols)]


def inverse_zigzag_scan(values, rows, cols):
    if len(values) != rows * cols:
        raise ValueError('Длина последовательности не совпадает с размером матрицы')

    matrix = [[0 for _ in range(cols)] for _ in range(rows)]
    for value, (r, c) in zip(values, zigzag_indices(rows, cols)):
        matrix[r][c] = value
    return matrix


def coefficient_category(value):
    value = int(value)
    if value == 0:
        return 0
    return int(math.floor(math.log2(abs(value)))) + 1


def value_to_additional_bits(value):
    value = int(value)
    size = coefficient_category(value)
    if size == 0:
        return ''
    if value > 0:
        return format(value, f'0{size}b')
    encoded_value = ((1 << size) - 1) + value
    return format(encoded_value, f'0{size}b')


def additional_bits_to_value(bits, size):
    if size == 0:
        return 0
    if len(bits) != size:
        raise ValueError('Неверная длина дополнительных битов')
    number = int(bits, 2)
    if bits[0] == '1':
        return number
    return number - ((1 << size) - 1)


def differential_encode_dc(dc_coeffs):
    if not dc_coeffs:
        return []
    result = [int(dc_coeffs[0])]
    for i in range(1, len(dc_coeffs)):
        result.append(int(dc_coeffs[i]) - int(dc_coeffs[i - 1]))
    return result


def differential_decode_dc(diff_codes):
    if not diff_codes:
        return []
    result = [int(diff_codes[0])]
    for i in range(1, len(diff_codes)):
        result.append(result[-1] + int(diff_codes[i]))
    return result


def rle_encode_ac(ac_coeffs):
    if len(ac_coeffs) != 63:
        raise ValueError('Для JPEG-блока ожидается ровно 63 AC коэффициента')

    last_nonzero = -1
    for i in range(62, -1, -1):
        if int(ac_coeffs[i]) != 0:
            last_nonzero = i
            break

    if last_nonzero == -1:
        return [(0, 0)]

    result = []
    zero_run = 0

    for i in range(last_nonzero + 1):
        value = int(ac_coeffs[i])
        if value == 0:
            zero_run += 1
            if zero_run == 16:
                result.append((15, 0))
                zero_run = 0
        else:
            result.append((zero_run, value))
            zero_run = 0

    if last_nonzero < 62:
        result.append((0, 0))

    return result


def rle_decode_ac(rle_codes):
    result = []
    for run, value in rle_codes:
        run = int(run)
        value = int(value)

        if run == 0 and value == 0:
            while len(result) < 63:
                result.append(0)
            break

        if run == 15 and value == 0:
            result.extend([0] * 16)
            continue

        result.extend([0] * run)
        result.append(value)

        if len(result) > 63:
            raise ValueError('RLE-кодирование повреждено: AC последовательность длиннее 63')

    while len(result) < 63:
        result.append(0)

    return result[:63]


def make_huffman_table(bits, values):
    code = 0
    k = 0
    table = {}
    decode_table = {}

    for bit_length, count in enumerate(bits, start=1):
        for _ in range(count):
            symbol = values[k]
            bit_string = format(code, f'0{bit_length}b')
            table[symbol] = bit_string
            decode_table[bit_string] = symbol
            code += 1
            k += 1
        code <<= 1

    return table, decode_table


def bits_from_counts(counts):
    if len(counts) != 16:
        raise ValueError('В списке counts должно быть 16 элементов')
    return [int(x) for x in counts]


# Стандартные таблицы Хаффмана baseline JPEG (Annex K)
STD_LUMINANCE_DC_BITS = bits_from_counts([0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0])
STD_LUMINANCE_DC_VALUES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

STD_CHROMINANCE_DC_BITS = bits_from_counts([0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
STD_CHROMINANCE_DC_VALUES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

STD_LUMINANCE_AC_BITS = bits_from_counts([0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 125])
STD_LUMINANCE_AC_VALUES = [
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61,
    0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52,
    0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25,
    0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
    0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64,
    0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x83,
    0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99,
    0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
    0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3,
    0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8,
    0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA
]

STD_CHROMINANCE_AC_BITS = bits_from_counts([0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 119])
STD_CHROMINANCE_AC_VALUES = [
    0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21, 0x31, 0x06, 0x12, 0x41, 0x51, 0x07, 0x61,
    0x71, 0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91, 0xA1, 0xB1, 0xC1, 0x09, 0x23, 0x33,
    0x52, 0xF0, 0x15, 0x62, 0x72, 0xD1, 0x0A, 0x16, 0x24, 0x34, 0xE1, 0x25, 0xF1, 0x17, 0x18,
    0x19, 0x1A, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44,
    0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63,
    0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A,
    0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97,
    0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4,
    0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA,
    0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7,
    0xE8, 0xE9, 0xEA, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA
]


STD_LUMA_DC_ENCODE, STD_LUMA_DC_DECODE = make_huffman_table(STD_LUMINANCE_DC_BITS, STD_LUMINANCE_DC_VALUES)
STD_CHROMA_DC_ENCODE, STD_CHROMA_DC_DECODE = make_huffman_table(STD_CHROMINANCE_DC_BITS, STD_CHROMINANCE_DC_VALUES)
STD_LUMA_AC_ENCODE, STD_LUMA_AC_DECODE = make_huffman_table(STD_LUMINANCE_AC_BITS, STD_LUMINANCE_AC_VALUES)
STD_CHROMA_AC_ENCODE, STD_CHROMA_AC_DECODE = make_huffman_table(STD_CHROMINANCE_AC_BITS, STD_CHROMINANCE_AC_VALUES)


def encode_dc_value(diff, dc_huffman_table):
    size = coefficient_category(diff)
    return dc_huffman_table[size] + value_to_additional_bits(diff)


def encode_ac_value(value):
    size = coefficient_category(value)
    return value_to_additional_bits(value), size


def encode_ac_rle_with_huffman(ac_coeffs, ac_huffman_table):
    bits = ''
    rle_codes = rle_encode_ac(ac_coeffs)

    for run, value in rle_codes:
        if run == 0 and value == 0:
            bits += ac_huffman_table[0x00]
            continue

        if run == 15 and value == 0:
            bits += ac_huffman_table[0xF0]
            continue

        amplitude_bits, size = encode_ac_value(value)
        symbol = (run << 4) | size
        bits += ac_huffman_table[symbol] + amplitude_bits

    return bits, rle_codes


def decode_huffman_symbol(bit_reader, decode_table):
    current = ''
    while True:
        current += bit_reader.read_bits(1)
        if current in decode_table:
            return decode_table[current]
        if len(current) > 16:
            raise ValueError('Не удалось декодировать код Хаффмана')


def decode_dc_value(bit_reader, dc_decode_table):
    size = decode_huffman_symbol(bit_reader, dc_decode_table)
    if size == 0:
        return 0
    bits = bit_reader.read_bits(size)
    return additional_bits_to_value(bits, size)


def decode_ac_rle_with_huffman(bit_reader, ac_decode_table):
    result = []

    while len(result) < 63:
        symbol = decode_huffman_symbol(bit_reader, ac_decode_table)

        if symbol == 0x00:
            result.extend([0] * (63 - len(result)))
            break

        if symbol == 0xF0:
            result.extend([0] * 16)
            continue

        run = (symbol >> 4) & 0x0F
        size = symbol & 0x0F

        result.extend([0] * run)
        bits = bit_reader.read_bits(size)
        value = additional_bits_to_value(bits, size)
        result.append(value)

        if len(result) > 63:
            raise ValueError('Ошибка декодирования AC: получено больше 63 коэффициентов')

    return result[:63]


def get_chrominance_quantization_matrix():
    return [
        [17, 18, 24, 47, 99, 99, 99, 99],
        [18, 21, 26, 66, 99, 99, 99, 99],
        [24, 26, 56, 99, 99, 99, 99, 99],
        [47, 66, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
    ]


def scale_quantization_matrix(q_matrix, quality):
    if not (1 <= quality < 100):
        raise ValueError('Quality должен быть в диапазоне [1, 100)')

    if quality < 50:
        s = 5000 / quality
    else:
        s = 200 - 2 * quality

    result = []
    for row in q_matrix:
        new_row = []
        for value in row:
            scaled = math.ceil((value * s) / 100.0)
            scaled = min(max(int(scaled), 1), 255)
            new_row.append(scaled)
        result.append(new_row)
    return result


def encode_block_to_bits(block, prev_dc, q_matrix, dc_huffman_table, ac_huffman_table):
    shifted = level_shift_block(block)
    coeffs = dct(shifted)
    quantized = quantize_dct(coeffs, q_matrix)
    zz = [int(x) for x in zigzag_scan(quantized)]

    dc = zz[0]
    dc_diff = dc - prev_dc
    dc_bits = encode_dc_value(dc_diff, dc_huffman_table)

    ac_bits, rle_codes = encode_ac_rle_with_huffman(zz[1:], ac_huffman_table)

    return {
        'bits': dc_bits + ac_bits,
        'dc': dc,
        'dc_diff': dc_diff,
        'zigzag': zz,
        'quantized': quantized,
        'rle_codes': rle_codes,
    }


def decode_block_from_bits(bit_reader, prev_dc, q_matrix, dc_decode_table, ac_decode_table):
    dc_diff = decode_dc_value(bit_reader, dc_decode_table)
    dc = prev_dc + dc_diff
    ac = decode_ac_rle_with_huffman(bit_reader, ac_decode_table)
    zz = [dc] + ac
    quantized = inverse_zigzag_scan(zz, 8, 8)
    dequantized = dequantize_dct(quantized, q_matrix)
    restored = inverse_level_shift_block(idct(dequantized))
    return restored, dc, zz, quantized


def channel_to_matrix(img):
    width, height = img.size
    matrix = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append(int(img.getpixel((x, y))))
        matrix.append(row)
    return matrix


def matrix_to_channel_image(matrix):
    height = len(matrix)
    width = len(matrix[0])
    img = Image.new('L', (width, height))
    for y in range(height):
        for x in range(width):
            value = int(round(matrix[y][x]))
            value = min(max(value, 0), 255)
            img.putpixel((x, y), value)
    return img


def split_image_into_channels(img):
    if img.mode == 'L':
        return {'Y': img.convert('L')}, 'GRAY'

    ycbcr = img.convert('YCbCr')
    y_channel, cb_channel, cr_channel = ycbcr.split()
    return {'Y': y_channel, 'Cb': cb_channel, 'Cr': cr_channel}, 'YCbCr'


def merge_channels_to_image(channels, color_space):
    if color_space == 'GRAY':
        return channels['Y'].convert('L')

    merged = Image.merge('YCbCr', (channels['Y'], channels['Cb'], channels['Cr']))
    return merged.convert('RGB')


class BitWriter:
    def __init__(self):
        self.bits = ''

    def write_bits(self, bits):
        self.bits += bits

    def get_bytes(self):
        padded_bits = self.bits
        while len(padded_bits) % 8 != 0:
            padded_bits += '1'
        data = bytearray()
        for i in range(0, len(padded_bits), 8):
            byte = int(padded_bits[i:i + 8], 2)
            data.append(byte)
            if byte == 0xFF:
                data.append(0x00)
        return bytes(data), len(self.bits)


class BitReader:
    def __init__(self, data, valid_bit_length):
        unstuffed = bytearray()
        i = 0
        while i < len(data):
            byte = data[i]
            unstuffed.append(byte)
            if byte == 0xFF and i + 1 < len(data) and data[i + 1] == 0x00:
                i += 2
            else:
                i += 1
        self.bits = ''.join(format(byte, '08b') for byte in unstuffed)[:valid_bit_length]
        self.position = 0

    def read_bits(self, count):
        if self.position + count > len(self.bits):
            raise ValueError('Недостаточно битов в потоке')
        result = self.bits[self.position:self.position + count]
        self.position += count
        return result


def get_default_huffman_spec():
    return {
        'luma_dc': {'bits': STD_LUMINANCE_DC_BITS, 'values': STD_LUMINANCE_DC_VALUES},
        'chroma_dc': {'bits': STD_CHROMINANCE_DC_BITS, 'values': STD_CHROMINANCE_DC_VALUES},
        'luma_ac': {'bits': STD_LUMINANCE_AC_BITS, 'values': STD_LUMINANCE_AC_VALUES},
        'chroma_ac': {'bits': STD_CHROMINANCE_AC_BITS, 'values': STD_CHROMINANCE_AC_VALUES},
    }


def compress_image_custom(input_image, output_file, quality=50):
    img = input_image
    if isinstance(input_image, str):
        img = Image.open(input_image)

    if img.mode not in ['RGB', 'L']:
        img = img.convert('RGB')

    channels, color_space = split_image_into_channels(img)

    luma_q = scale_quantization_matrix(get_standard_quantization_matrix(), quality)
    chroma_q = scale_quantization_matrix(get_chrominance_quantization_matrix(), quality)

    writer = BitWriter()
    metadata = {
        'magic': 'MYJPEG1',
        'width': img.width,
        'height': img.height,
        'quality': quality,
        'color_space': color_space,
        'block_size': [8, 8],
        'quantization_tables': {
            'Y': luma_q,
            'Cb': chroma_q,
            'Cr': chroma_q,
        },
        'huffman_tables': get_default_huffman_spec(),
        'components': [],
    }

    debug_info = {}

    for component_name, channel_img in channels.items():
        matrix = channel_to_matrix(channel_img)
        blocks, original_h, original_w, padded_h, padded_w = split_into_blocks(matrix, 8, 8, pad=True)

        component_info = {
            'name': component_name,
            'original_size': [original_w, original_h],
            'padded_size': [padded_w, padded_h],
            'blocks_w': len(blocks[0]),
            'blocks_h': len(blocks),
            'bit_length_start': len(writer.bits),
        }

        if component_name == 'Y':
            dc_table = STD_LUMA_DC_ENCODE
            ac_table = STD_LUMA_AC_ENCODE
            q_matrix = luma_q
        else:
            dc_table = STD_CHROMA_DC_ENCODE
            ac_table = STD_CHROMA_AC_ENCODE
            q_matrix = chroma_q

        prev_dc = 0
        first_debug = None

        for block_row in blocks:
            for block in block_row:
                encoded = encode_block_to_bits(block, prev_dc, q_matrix, dc_table, ac_table)
                writer.write_bits(encoded['bits'])
                prev_dc = encoded['dc']
                if first_debug is None:
                    first_debug = encoded

        component_info['bit_length_end'] = len(writer.bits)
        metadata['components'].append(component_info)
        debug_info[component_name] = first_debug

    payload, valid_bit_length = writer.get_bytes()
    metadata['valid_bit_length'] = valid_bit_length

    meta_json = json.dumps(metadata, ensure_ascii=False).encode('utf-8')
    with open(output_file, 'wb') as f:
        f.write(b'MYJPEG1')
        f.write(struct.pack('>I', len(meta_json)))
        f.write(meta_json)
        f.write(payload)

    return {
        'metadata': metadata,
        'debug_info': debug_info,
        'payload_size': len(payload),
        'file_size': os.path.getsize(output_file),
    }


def decompress_image_custom(input_file):
    with open(input_file, 'rb') as f:
        magic = f.read(7)
        if magic != b'MYJPEG1':
            raise ValueError('Неверный формат файла')
        meta_size = struct.unpack('>I', f.read(4))[0]
        metadata = json.loads(f.read(meta_size).decode('utf-8'))
        payload = f.read()

    bit_reader = BitReader(payload, metadata['valid_bit_length'])
    restored_channels = {}

    for component in metadata['components']:
        component_name = component['name']
        padded_w, padded_h = component['padded_size']
        original_w, original_h = component['original_size']
        blocks_w = component['blocks_w']
        blocks_h = component['blocks_h']

        if component_name == 'Y':
            q_matrix = metadata['quantization_tables']['Y']
            dc_decode = STD_LUMA_DC_DECODE
            ac_decode = STD_LUMA_AC_DECODE
        else:
            q_matrix = metadata['quantization_tables'][component_name]
            dc_decode = STD_CHROMA_DC_DECODE
            ac_decode = STD_CHROMA_AC_DECODE

        restored_blocks = []
        prev_dc = 0

        for _ in range(blocks_h):
            row_blocks = []
            for _ in range(blocks_w):
                block, prev_dc, _, _ = decode_block_from_bits(bit_reader, prev_dc, q_matrix, dc_decode, ac_decode)
                row_blocks.append(block)
            restored_blocks.append(row_blocks)

        restored_matrix = merge_blocks(restored_blocks, original_h, original_w, 8, 8)
        restored_channels[component_name] = matrix_to_channel_image(restored_matrix)

    image = merge_channels_to_image(restored_channels, metadata['color_space'])
    return image, metadata


def save_decompressed_image(input_file, output_image_path):
    image, metadata = decompress_image_custom(input_file)
    image.save(output_image_path)
    return image, metadata


def main():
    input_file = '/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/Китенок.png'

    # Исходное цветное изображение
    color_img = Image.open(input_file).convert('RGB')

    # 3. Изображение в оттенках серого
    gray_img = color_img.convert('L')
    # gray_img.show()
    gray_img.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/3_grayscale.png')

    # 4. Черно-белое без дизеринга, по сути округление к 0 и 255
    bw_rounded_img = gray_img.convert('1', dither=Image.Dither.NONE)
    bw_rounded_img.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/4_bw_rounded.png')
    # bw_rounded_img.show()

    # 5. Черно-белое с дизерингом
    bw_dither_img = color_img.convert('1')
    bw_dither_img.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/5_bw_dither.png')
    # bw_dither_img.show()

    print('Файлы PNG созданы.')
    print()

    # Перевод в raw
    print('2. Цветное изображение:')
    info_color = convert_to_raw(input_file, '/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/Китенок.raw')
    calculate_koeff(info_color)
    print()

    print('3. Оттенки серого:')
    info_gray = convert_to_raw('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/3_grayscale.png', '/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/3_grayscale.raw')
    calculate_koeff(info_gray)
    print()

    print('4. ЧБ без дизеринга:')
    info_bw_rounded = convert_to_raw('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/4_bw_rounded.png', '/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/4_bw_rounded.raw')
    calculate_koeff(info_bw_rounded)
    print()

    print('5. ЧБ с дизерингом:')
    info_bw_dither = convert_to_raw('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/5_bw_dither.png', '/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/1 задание/5_bw_dither.raw')
    calculate_koeff(info_bw_dither)

    # RGB -> YCbCr
    ycbcr_img = rgb_to_ycbcr(color_img)
    ycbcr_img.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/2 задание/6_ycbcr.png')
    # ycbcr_img.show()

    # обратно YCbCr -> RGB
    rgb_back = ycbcr_to_rgb(ycbcr_img)
    rgb_back.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/2 задание/7_rgb_restored.png')
    # rgb_back.show()

    print('Преобразование RGB -> YCbCr -> RGB выполнено')
    compare_images(color_img, rgb_back)
    print()

    save_raw_with_meta(ycbcr_img, '/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/2 задание/6_ycbcr.raw', 'YCbCr')

    down_img = downsample(color_img, 2) # Необходимо, чтобы высота и ширина нацело делились на k
    down_img.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/down_x2.png')

    up_img = upsample(down_img, 2) # Необходимо, чтобы высота и ширина нацело делились на k
    up_img.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/up_x2.png')


    print('Даунсэмплинг и апсэмплинг выполнены')
    print(f'Размер исходного изображения: {color_img.size}')
    print(f'Размер после downsampling: {down_img.size}')
    print(f'Размер после upsampling: {up_img.size}')
    compare_images(color_img, up_img)
    print()

    down4 = downsample(color_img, 4)
    down4.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/10_downsample_x4.png')

    up4 = upsample(down4, 4)
    up4.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/11_upsample_from_x4.png')

    print('Проверка пикселизации при коэффициенте децимации 4')
    compare_images(color_img, up4)
    print()

    print('Пример линейной интерполяции:')
    value1 = linear_interpolation(0, 10, 100, 200, 4)
    print(f'linear_interpolation(0, 10, 100, 200, 4) = {value1}')
    print()

    print('Пример линейного сплайна:')
    xs = [0, 2, 4, 6, 8]
    ys = [0, 10, 20, 15, 30]
    value2 = linear_spline(xs, ys, 5)
    print(f'linear_spline([0, 2, 4, 6, 8], [0, 10, 20, 15, 30], 5) = {value2}')
    print()

    print('Пример билинейной интерполяции:')
    value3 = bilinear_interpolation(0, 1, 0, 1, 10, 20, 30, 40, 0.5, 0.5)
    print(f'bilinear_interpolation(...) = {value3}')
    print()

    resized_half = resize_bilinear(color_img, color_img.width // 2, color_img.height // 2)
    resized_half.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/12_resize_half_bilinear.png')

    resized_back = resize_bilinear(resized_half, color_img.width, color_img.height)
    resized_back.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/13_resize_back_bilinear.png')

    print('Изменение размера билинейной интерполяцией выполнено')
    print(f'Размер после уменьшения: {resized_half.size}')
    print(f'Размер после восстановления: {resized_back.size}')
    compare_images(color_img, resized_back)
    print()

    # ====================================================================
    # 3. Дискретное косинусное преобразование
    print('Проверка ДКП для блока 8x8 и всего изображения')
    gray_matrix = image_to_matrix(gray_img)

    blocks, _, _, _, _ = split_into_blocks(gray_matrix, 8, 8, pad=True)
    first_block = blocks[0][0]
    shifted_first_block = level_shift_block(first_block)

    coeffs_primitive = dct(shifted_first_block)
    restored_primitive = inverse_level_shift_block(idct(coeffs_primitive))

    coeffs_matrix = dct_matrix(shifted_first_block)
    restored_matrix = inverse_level_shift_block(idct_matrix(coeffs_matrix))

    print('Максимальное отличие исходного блока и IDCT(DCT(block)) [примитивный способ]:')
    print(f'{max_abs_difference_matrix(first_block, restored_primitive):.10f}')
    print('Максимальное отличие коэффициентов двух реализаций ДКП:')
    print(f'{max_abs_difference_matrix(coeffs_primitive, coeffs_matrix):.10f}')
    print()

    q_matrix = get_standard_quantization_matrix()
    quantized = quantize_dct(coeffs_primitive, q_matrix)
    dequantized = dequantize_dct(quantized, q_matrix)
    restored_quantized = inverse_level_shift_block(idct(dequantized))

    print('Пример квантованных коэффициентов первого блока:')
    print_matrix(quantized, digits=0)
    print()
    print('Максимальное отличие блока после квантования и восстановления:')
    print(f'{max_abs_difference_matrix(first_block, restored_quantized):.10f}')
    print()

    restored_full_primitive = process_blocks_with_dct(gray_matrix, 8, 8, q_matrix=None, use_matrix_method=False)
    restored_full_matrix = process_blocks_with_dct(gray_matrix, 8, 8, q_matrix=None, use_matrix_method=True)
    restored_full_quantized = process_blocks_with_dct(gray_matrix, 8, 8, q_matrix=q_matrix, use_matrix_method=False)

    restored_img_primitive = matrix_to_image(restored_full_primitive)
    restored_img_matrix = matrix_to_image(restored_full_matrix)
    restored_img_quantized = matrix_to_image(restored_full_quantized)

    restored_img_primitive.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/3 задание/dct_restored_primitive.png')
    restored_img_matrix.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/3 задание/dct_restored_matrix.png')
    restored_img_quantized.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/3 задание/dct_restored_quantized.png')

    print('Сравнение исходного grayscale и восстановленного после ДКП/ОДКП:')
    compare_images(gray_img.convert('RGB'), restored_img_primitive.convert('RGB'))
    print('Сравнение исходного grayscale и восстановленного после матричного ДКП/ОДКП:')
    compare_images(gray_img.convert('RGB'), restored_img_matrix.convert('RGB'))
    print('Сравнение исходного grayscale и восстановленного после квантования:')
    compare_images(gray_img.convert('RGB'), restored_img_quantized.convert('RGB'))


    print()
    print('Проверка зигзаг-обхода:')
    test_square = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    test_rect = [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
    ]
    print(f'Зигзаг 3x3: {zigzag_scan(test_square)}')
    print(f'Зигзаг 2x4: {zigzag_scan(test_rect)}')
    print()

    print('Проверка DC-difference, RLE, VLC и Хаффмана:')
    first_block_zigzag = zigzag_scan(quantized)
    dc_coeffs_example = [first_block_zigzag[0], first_block_zigzag[0] + 3, first_block_zigzag[0] - 2]
    dc_diff_example = differential_encode_dc(dc_coeffs_example)
    print(f'DC коэффициенты: {dc_coeffs_example}')
    print(f'Разностное кодирование DC: {dc_diff_example}')
    print(f'VLC для первого DC diff: {encode_dc_value(dc_diff_example[0], STD_LUMA_DC_ENCODE)}')
    ac_rle_example = rle_encode_ac(first_block_zigzag[1:])
    print(f'RLE AC первого блока: {ac_rle_example[:10]}')
    ac_bits_example, _ = encode_ac_rle_with_huffman(first_block_zigzag[1:], STD_LUMA_AC_ENCODE)
    print(f'Первые биты AC после Huffman/VLC: {ac_bits_example[:64]}...')
    print()

    print('Проверка масштабирования таблицы квантования по Quality:')
    q30 = scale_quantization_matrix(get_standard_quantization_matrix(), 30)
    q80 = scale_quantization_matrix(get_standard_quantization_matrix(), 80)
    print('Q=30, первая строка:', q30[0])
    print('Q=80, первая строка:', q80[0])
    print()

    print('Проверка записи сжатого файла и декомпрессии:')
    compressed_info = compress_image_custom(gray_img, '/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/4 задание/compressed_gray.myjpg', quality=50)
    restored_custom_img, restored_meta = decompress_image_custom('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/4 задание/compressed_gray.myjpg')
    restored_custom_img.save('/Users/viacheslav/Desktop/Подготовка ко 2 лабе АиСД/4 задание/restored_gray_from_myjpg.png')
    print(f"Размер сжатого файла: {compressed_info['file_size']} байт")
    print(f"Размер битового потока: {compressed_info['payload_size']} байт")
    print(f"Цветовое пространство в метаданных: {restored_meta['color_space']}")
    compare_images(gray_img.convert('RGB'), restored_custom_img.convert('RGB'))
    print()
    print('Оценка сложности:')
    print('1) Примитивное 2D ДКП для блока NxM: O(N^2 * M^2)')
    print('2) Для блока 8x8 это константное время, но с большим числом операций')
    print('3) Коэффициенты ДКП нужно хранить в вещественном типе: float')

if __name__ == '__main__':
    main()
