package associative_array;

import java.util.Random;

public class Main {
    // Константы для тестирования
    private static final int INITIAL_ELEMENTS_COUNT = 8;
    private static final int[] TEST_KEYS = {1, 5, 4, 2, 3, 9, 1, 17};
    private static final Object[] TEST_VALUES = {1, 5, 4, 2, 3, 9, 10, 17};
    private static final int[] SEARCH_KEYS = {9, 1};
    private static final int[] CONTAINS_KEYS = {5, 10, 17};
    private static final int REMOVE_KEY = 5;

    // Константы для теста с большим количеством элементов
    private static final int MANY_ELEMENTS_COUNT = 1000;
    private static final int SEARCH_ELEMENTS_COUNT = 200;
    private static final int RANDOM_RANGE = 2000;
    private static final long RANDOM_SEED = 123L;

    // Константы для преобразования времени
    private static final double NANOSECONDS_TO_MICROSECONDS = 1000.0;
    private static final double NANOSECONDS_TO_MILLISECONDS = 1_000_000.0;

    public static void main(String[] args) {
        System.out.println("Сравнительный анализ пробирований\n");

        Hash_table linearTable = new Hash_table();
        linearTable.setUseQuadraticProbing(false);

        Hash_table quadTable = new Hash_table();
        quadTable.setUseQuadraticProbing(true);

        System.out.println("1. Линейное:");
        testOperations(linearTable);

        System.out.println("\n2. Квадратичное:");
        testOperations(quadTable);

        System.out.println("\n3. Тест на 1000 элементов:");
        testManyElements();
    }

    private static void testOperations(Hash_table table) {
        long startTime = System.nanoTime();

        // Вставка тестовых элементов
        for (int i = 0; i < INITIAL_ELEMENTS_COUNT; i++) {
            table.AddElement(TEST_KEYS[i], TEST_VALUES[i]);
        }

        // Поиск значений
        System.out.println("Значение по ключу 9: " + table.get_value(9));
        System.out.println("Значение по ключу 1: " + table.get_value(1));

        System.out.println("\nВсе элементы:");
        table.print();

        System.out.println("\nПроверка ключей:");
        for (int key : CONTAINS_KEYS) {
            System.out.println("Ключ " + key + ": " + table.containsKey(key));
        }

        System.out.println("\nУдаляем ключ 5: " + table.Remove(REMOVE_KEY));
        System.out.println("Ключ 5 после удаления: " + table.containsKey(REMOVE_KEY));

        long endTime = System.nanoTime();
        double executionTimeMicroseconds = (endTime - startTime) / NANOSECONDS_TO_MICROSECONDS;
        System.out.println("Время выполнения: " + (int)executionTimeMicroseconds + " мкс");
    }

    private static void testManyElements() {
        Random rand = new Random(RANDOM_SEED);

        // Линейное пробирование
        Hash_table linear = new Hash_table();
        linear.setUseQuadraticProbing(false);

        long linearStart = System.nanoTime();
        for (int i = 0; i < MANY_ELEMENTS_COUNT; i++) {
            int key = rand.nextInt(RANDOM_RANGE);
            linear.AddElement(key, "value" + key);
        }
        long linearTime = System.nanoTime() - linearStart;

        rand = new Random(RANDOM_SEED);
        int linearFounds = 0;
        for (int i = 0; i < SEARCH_ELEMENTS_COUNT; i++) {
            int key = rand.nextInt(RANDOM_RANGE);
            if (linear.get_value(key) != null) {
                linearFounds++;
            }
        }

        // Квадратичное пробирование
        Hash_table quad = new Hash_table();
        quad.setUseQuadraticProbing(true);

        rand = new Random(RANDOM_SEED);
        long quadStart = System.nanoTime();
        for (int i = 0; i < MANY_ELEMENTS_COUNT; i++) {
            int key = rand.nextInt(RANDOM_RANGE);
            quad.AddElement(key, "value" + key);
        }
        long quadTime = System.nanoTime() - quadStart;

        rand = new Random(RANDOM_SEED);
        int quadFounds = 0;
        for (int i = 0; i < SEARCH_ELEMENTS_COUNT; i++) {
            int key = rand.nextInt(RANDOM_RANGE);
            if (quad.get_value(key) != null) {
                quadFounds++;
            }
        }

        System.out.println("Линейное пробирование:");
        double linearTimeMs = linearTime / NANOSECONDS_TO_MILLISECONDS;
        System.out.println("  Время вставки " + MANY_ELEMENTS_COUNT + " элементов: " +
                String.format("%.3f", linearTimeMs) + " мс");
        System.out.println("  Найдено элементов при поиске: " + linearFounds + "/" + SEARCH_ELEMENTS_COUNT);

        System.out.println("\nКвадратичное пробирование:");
        double quadTimeMs = quadTime / NANOSECONDS_TO_MILLISECONDS;
        System.out.println("  Время вставки " + MANY_ELEMENTS_COUNT + " элементов: " +
                String.format("%.3f", quadTimeMs) + " мс");
        System.out.println("  Найдено элементов при поиске: " + quadFounds + "/" + SEARCH_ELEMENTS_COUNT);

        System.out.println("\nВЫВОД:");
        double timeDifferencePercent = ((double) quadTime / linearTime - 1) * 100;
        System.out.println("Разница во времени (+лин/-квадр): " +
                String.format("%.1f", timeDifferencePercent) + "%");
    }
}