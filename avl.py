from bst import BST, Node
import math
import random
import matplotlib.pyplot as plt


# Класс узла AVL дерева
class AVLNode(Node):
    def __init__(self, key):
        super().__init__(key)
        self.height = 1  # Высота узла (новое поле для AVL)

    def __str__(self) -> str:
        return f"{self.key}(h={self.height})"  # Добавляем высоту в вывод


# Класс AVL дерева
class AVL(BST):
    def __init__(self):
        super().__init__()

    def _node_str(self, node) -> str:
        """Переопределяем для отображения высоты"""
        return str(node)

    def _create_node(self, key):
        """Создание AVL узла"""
        return AVLNode(key)

    # Вспомогательные методы для AVL дерева
    def _get_height(self, node):
        """Получить высоту узла"""
        if self._is_empty(node):
            return 0
        return node.height

    def _update_height(self, node):
        """Обновить высоту узла"""
        if not self._is_empty(node):
            left_height = self._get_height(node.leftch)
            right_height = self._get_height(node.rightch)
            node.height = max(left_height, right_height) + 1

    def getheight(self, node=None) -> int:
        """Получить высоту дерева (используем сохраненную высоту)"""
        if node is None:
            node = self.root
            if self._is_empty(node):
                return 0
        return self._get_height(node)

    def _get_balance(self, node):
        """Получить баланс-фактор узла"""
        if self._is_empty(node):
            return 0
        return self._get_height(node.leftch) - self._get_height(node.rightch)

    def _right_rotate(self, y):
        """Правый поворот"""
        x = y.leftch
        T2 = x.rightch

        # Выполняем поворот
        x.rightch = y
        y.leftch = T2

        # Обновляем родителей
        if not self._is_empty(T2):
            T2.parent = y
        x.parent = y.parent
        y.parent = x

        # Обновляем высоты
        self._update_height(y)
        self._update_height(x)

        return x

    def _left_rotate(self, x):
        """Левый поворот"""
        y = x.rightch
        T2 = y.leftch

        # Выполняем поворот
        y.leftch = x
        x.rightch = T2

        # Обновляем родителей
        if not self._is_empty(T2):
            T2.parent = x
        y.parent = x.parent
        x.parent = y

        # Обновляем высоты
        self._update_height(x)
        self._update_height(y)

        return y

    def _balance_node(self, node):
        """Балансировка узла"""
        if self._is_empty(node):
            return node

        # Обновляем высоту текущего узла
        self._update_height(node)

        # Получаем баланс-фактор
        balance = self._get_balance(node)

        # Левый левый случай
        if balance > 1 and self._get_balance(node.leftch) >= 0:
            return self._right_rotate(node)

        # Правый правый случай
        if balance < -1 and self._get_balance(node.rightch) <= 0:
            return self._left_rotate(node)

        # Левый правый случай
        if balance > 1 and self._get_balance(node.leftch) < 0:
            node.leftch = self._left_rotate(node.leftch)
            return self._right_rotate(node)

        # Правый левый случай
        if balance < -1 and self._get_balance(node.rightch) > 0:
            node.rightch = self._right_rotate(node.rightch)
            return self._left_rotate(node)

        return node

    def _insert_recursive(self, node, key, parent=None):
        """Рекурсивная вставка узла"""
        # Обычная вставка в бинарное дерево поиска
        if self._is_empty(node):
            newNode = self._create_node(key)
            newNode.parent = parent
            return newNode

        if key < node.key:
            node.leftch = self._insert_recursive(node.leftch, key, node)
        else:
            node.rightch = self._insert_recursive(node.rightch, key, node)

        # Балансировка дерева
        return self._balance_node(node)

    def insert(self, key):
        """Вставка нового ключа в дерево с балансировкой"""
        self.root = self._insert_recursive(self.root, key)

    def _delete_recursive(self, node, key):
        """Рекурсивное удаление узла с балансировкой"""
        if self._is_empty(node):
            return node

        if key < node.key:
            node.leftch = self._delete_recursive(node.leftch, key)
        elif key > node.key:
            node.rightch = self._delete_recursive(node.rightch, key)
        else:
            # Узел найден, удаляем его
            if self._is_empty(node.leftch) or self._is_empty(node.rightch):
                # Случай 1 или 2: нет потомков или один потомок
                if not self._is_empty(node.leftch):
                    temp = node.leftch
                else:
                    temp = node.rightch

                if self._is_empty(temp):
                    # Нет потомков
                    temp = node
                    node = self._create_empty_child()
                else:
                    # Один потомок
                    temp.parent = node.parent
                    node = temp
            else:
                # Случай 4: два потомка
                temp = self._find_min_node(node.rightch)
                node.key = temp.key
                node.rightch = self._delete_recursive(node.rightch, temp.key)

        if self._is_empty(node):
            return node

        # Балансировка дерева
        return self._balance_node(node)

    def deleteValue(self, key):
        """Удаление узла по ключу с балансировкой"""
        if not self._is_empty(self.findNode(key)):
            self.root = self._delete_recursive(self.root, key)
            return True
        return False

    def delete_node(self, delNode):
        """Вспомогательный метод удаления (аналогично BST для совместимости)"""
        if self._is_empty(delNode):
            return None

        key = delNode.key
        self.root = self._delete_recursive(self.root, key)
        return self.root


# Теоретические оценки высоты для AVL дерева
def avl_theoretical_lower_bound(n):
    """Нижняя оценка высоты AVL-дерева: log₂(n+1)"""
    if n == 0:
        return 0
    return math.log2(n + 1)


def avl_theoretical_upper_bound(n):
    """Верхняя оценка высоты AVL-дерева: 1.44*log₂(n+2)"""
    if n == 0:
        return 0
    return 1.44 * math.log2(n + 2)


def avl_experiment_random_keys():
    """Эксперимент со случайными ключами для AVL"""
    max_n = 20000
    step = 100
    n_values = []
    heights = []
    lower_bounds = []
    upper_bounds = []

    # Создаем массив всех возможных ключей
    all_keys = list(range(max_n))
    random.shuffle(all_keys)

    for n in range(0, max_n + 1, step):
        n_values.append(n)

        if n == 0:
            # Пустое дерево
            height = 0
        else:
            # Создаем новое дерево
            tree = AVL()

            # Вставляем n случайных ключей
            for i in range(n):
                tree.insert(all_keys[i])

            # Измеряем высоту
            height = tree.getheight()

        heights.append(height)

        # Рассчитываем теоретические оценки для AVL
        lower_bounds.append(avl_theoretical_lower_bound(n))
        upper_bounds.append(avl_theoretical_upper_bound(n))

    return n_values, heights, lower_bounds, upper_bounds


def avl_experiment_sorted_keys():
    """Эксперимент с монотонно возрастающими ключами для AVL"""
    max_n = 20000
    step = 100
    n_values = []
    heights = []
    lower_bounds = []
    upper_bounds = []

    for n in range(0, max_n + 1, step):
        n_values.append(n)

        if n == 0:
            # Пустое дерево
            height = 0
        else:
            # Создаем новое дерево
            tree = AVL()

            # Вставляем n монотонно возрастающих ключей
            for i in range(n):
                tree.insert(i)

            # Измеряем высоту
            height = tree.getheight()

        heights.append(height)

        # Рассчитываем теоретические оценки для AVL
        lower_bounds.append(avl_theoretical_lower_bound(n))
        upper_bounds.append(avl_theoretical_upper_bound(n))

    return n_values, heights, lower_bounds, upper_bounds


def plot_avl_results():
    """Построение двух графиков для AVL дерева (как на скриншоте)"""

    # Получаем данные для обоих экспериментов
    n_rand, h_rand, lb_rand, ub_rand = avl_experiment_random_keys()
    n_sorted, h_sorted, lb_sorted, ub_sorted = avl_experiment_sorted_keys()

    # Создаем фигуру с двумя подграфиками
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # График 1: случайные ключи
    ax1.plot(n_rand, h_rand, 'b-', label='Экспериментальная высота', linewidth=2, alpha=0.7)
    ax1.plot(n_rand, lb_rand, 'r--', label='Теоретическая нижняя оценка', linewidth=1.5)
    ax1.plot(n_rand, ub_rand, 'g--', label='Теоретическая верхняя оценка', linewidth=1.5)
    ax1.set_xlabel('Количество ключей (n)')
    ax1.set_ylabel('Высота дерева')
    ax1.set_title('Зависимость высоты AVL-дерева от n\n(случайные ключи)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, max(n_rand))

    # График 2: монотонно возрастающие ключи
    ax2.plot(n_sorted, h_sorted, 'b-', label='Экспериментальная высота', linewidth=2, alpha=0.7)
    ax2.plot(n_sorted, lb_sorted, 'r--', label='Теоретическая нижняя оценка', linewidth=1.5)
    ax2.plot(n_sorted, ub_sorted, 'g--', label='Теоретическая верхняя оценка', linewidth=1.5)
    ax2.set_xlabel('Количество ключей (n)')
    ax2.set_ylabel('Высота дерева')
    ax2.set_title('Зависимость высоты AVL-дерева от n\n(монотонно возрастающие ключи)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, max(n_sorted))

    plt.tight_layout()
    plt.show()


# Основная программа
if __name__ == "__main__":
    # Тестирование дерева
    Tree = AVL()

    # Создание случайных данных
    unique_random_numbers = random.sample(range(-10, 26), 20)

    # Вставка всех чисел
    for n in unique_random_numbers:
        Tree.insert(n)

    # Вывод дерева
    print("=" * 60)
    print("AVL дерево после вставки 20 элементов:")
    print("=" * 60)
    print(Tree)
    print(f"\nВысота дерева = {Tree.getheight()}\n")

    print("=" * 60)
    # Поиск случайного узла
    found_node = Tree.findNode(random.choice(unique_random_numbers))
    if found_node:
        print(f'''\nЗначение узла = {found_node.key};
    Родитель: {found_node.parent.key if found_node.parent else "None"},
    Левый потомок: {found_node.leftch.key if found_node.leftch else "None"},
    Правый потомок: {found_node.rightch.key if found_node.rightch else "None"},
    Высота узла: {found_node.height}.''')

    # Попытка найти несуществующий узел
    found_node = Tree.findNode(-1000)
    print(f"\nПоиск -1000: {found_node}")

    # Минимум и максимум
    print(f"\nМинимум =", Tree.findMin())
    print(f"Максимум =", Tree.findMax())

    # Различные обходы
    print("Различные обходы дерева:")
    print(f"Центрированный обход = {Tree.inOrderTraversal()}")
    print(f"Прямой обход = {Tree.preOrderTraversal()}")
    print(f"Обратный обход = {Tree.postOrderTraversal()}")
    print(f"По уровням/в ширину = {Tree.levelOrderTraversal()}")

    # Удаление 3 узлов
    deleted_nodes = random.sample(unique_random_numbers, 3)
    for key in deleted_nodes:
        Tree.deleteValue(key)

    # Дерево после удаления
    # Проверка на пустоту
    print(f"\nДерево пустое? {Tree.isEmpty()}")

    print("\n" + "=" * 60 + "\n")

    print("Балансировка после вставки 3 случайных элементов:\n")
    random_elements = random.sample(range(-50, 50), 1)
    print(f"Вставляем 1 случайный элемент: {random_elements}")

    for elem in random_elements:
        Tree.insert(elem)
        print(f"\nПосле вставки {elem}:")
        print(Tree)
        print(f"\nВысота после вставки = {Tree.getheight()}")

    print("\n" + "=" * 60)

    print(f"\nAVL дерево после удаления 3 элементов:\n")
    print(f"Удаляем 3 элемента: {deleted_nodes}\n")
    print(Tree)

    print(f"\nВысота дерева после удаления = {Tree.getheight()}\n")

    print("=" * 60)
    print(f"\nСтроим графики...")
    # Запускаем построение графиков
    plot_avl_results()
