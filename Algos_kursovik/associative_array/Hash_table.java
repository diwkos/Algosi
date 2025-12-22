package associative_array;

import java.util.Random;

class Hash_table {
    // Константы для настройки хеш-таблицы
    private static final int DEFAULT_CAPACITY = 16;
    private static final double LOAD_FACTOR_THRESHOLD = 0.5;
    private static final int POLY_COEFF_COUNT = 5;

    class Pair {
        public int key;
        public Object value;
        public boolean deleted;

        public Pair(int key, Object value) {
            this.key = key;
            this.value = value;
            this.deleted = false;
        }
    }

    private Pair[] PairArray;
    private int Capacity = DEFAULT_CAPACITY;
    private int[] CoeffArray = new int[POLY_COEFF_COUNT];
    private int size = 0;
    private boolean useQuadraticProbing = false;

    public Hash_table() {
        PairArray = new Pair[Capacity];
        CalculatePolyCoeff();
    }

    public void setUseQuadraticProbing(boolean useQuadratic) {
        this.useQuadraticProbing = useQuadratic;
    }

    private void CalculatePolyCoeff() {
        Random rn = new Random();
        for (int i = 0; i < CoeffArray.length; i++) {
            CoeffArray[i] = rn.nextInt();
        }
    }

    private int new_Hashfun(int key) {
        int newHash = CoeffArray[0];
        int OldHash = key;
        for (int i = 0; i < CoeffArray.length - 1; i++) {
            newHash = newHash * OldHash + CoeffArray[i + 1];
        }
        return Math.abs(newHash % Capacity);
    }

    // Линейное пробирование
    private int Lin_Probing(int index, int attempt) {
        return (index + attempt) % Capacity;
    }

    // Квадратичное пробирование
    private int Quad_Probing(int index, int attempt) {
        return (index + attempt * attempt) % Capacity;
    }

    private int probe(int index, int attempt) {
        return useQuadraticProbing ? Quad_Probing(index, attempt) : Lin_Probing(index, attempt);
    }

    public void AddElement(int key, Object value) {
        int index = new_Hashfun(key);
        int attempt = 0; // попытка (итерация), нужна отдельная переменная, для того, чтобы передать ее в нужное пробирование

        for (; attempt < Capacity; attempt++) {
            int currentIndex = probe(index, attempt); // пробируем

            if (PairArray[currentIndex] == null || PairArray[currentIndex].deleted) { // ничего -> добавляем
                PairArray[currentIndex] = new Pair(key, value);
                size++;
                break;
            } else if (PairArray[currentIndex].key == key) { // совпадает -> заменяем
                PairArray[currentIndex].value = value;
                if (PairArray[currentIndex].deleted) {
                    PairArray[currentIndex].deleted = false;
                    size++;
                }
                break;
            }
        }

        if ((double)size / Capacity > LOAD_FACTOR_THRESHOLD) { // если размер превышает половину, то resize
            upResize();
        }
    }

    private void upResize() {
        int newCapacity = Capacity * 2;
        if (newCapacity < 0) {
            throw new IllegalArgumentException("");
        }
        Pair[] OldArray = PairArray;
        PairArray = new Pair[newCapacity];
        Capacity = newCapacity;
        CalculatePolyCoeff();
        size = 0;

        for (Pair pair : OldArray) {
            if (pair != null && !pair.deleted) {
                AddElement(pair.key, pair.value);
            }
        }
    }

    public Object get_value(int key) {
        int index = new_Hashfun(key);
        for (int attempt = 0; attempt < Capacity; attempt++) {
            int currentIndex = probe(index, attempt); // пробируем

            if (PairArray[currentIndex] == null) { // если null -> значит нет
                return null;
            }

            if (!PairArray[currentIndex].deleted && PairArray[currentIndex].key == key) { //совпадает -> возвращаем
                return PairArray[currentIndex].value;
            }
        }
        return null;
    }

    // Проверка наличия ключа
    public boolean containsKey(int key) {
        return get_value(key) != null;
    }

    public boolean Remove(int key) {
        int index = new_Hashfun(key);

        for (int attempt = 0; attempt < Capacity; attempt++) {
            int currentIndex = probe(index, attempt); // пробируем

            if (PairArray[currentIndex] == null) { // null -> нет
                return false;
            }

            if (!PairArray[currentIndex].deleted && PairArray[currentIndex].key == key) { // совпадают -> помечаем как удаленные
                PairArray[currentIndex].deleted = true;
                size--;
                return true;
            }
        }
        return false;
    }

    public void print() {
        for (Pair pair : PairArray) {
            if (pair != null && !pair.deleted) {
                System.out.println("Ключ: " + pair.key + ", Значение: " + pair.value);
            }
        }
    }
}