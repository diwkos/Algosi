from bst import BST, Node
import math
import random
import matplotlib.pyplot as plt

# Константы для цвета узлов
RED = "RED"
BLACK = "BLACK"


# Класс узла красно-черного дерева
class RBNode(Node):
    def __init__(self, key):
        super().__init__(key)
        self.color = RED  # Цвет узла
        # Переименовываем для совместимости с BST
        self.leftch = None  # Левый потомок
        self.rightch = None  # Правый потомок

    def __str__(self) -> str:
        color_str = "R" if self.color == RED else "B"
        return f"{self.key}({color_str})"


# Класс красно-черного дерева
class RBTree(BST):
    def __init__(self):
        super().__init__()
        # Создаем специальный NIL узел для RB дерева
        self.NIL = self._create_nil_node()
        self.root = self.NIL

    def _create_nil_node(self):
        """Создание NIL узла (лист дерева)"""
        nil = RBNode(0)
        nil.key = None
        nil.color = BLACK
        nil.leftch = None
        nil.rightch = None
        nil.parent = None
        return nil

    def __str__(self, node=None, level=1) -> str:
        """Переопределяем метод для отображения NIL вместо None"""
        # Начало рекурсии
        if node is None:
            node = self.root
            if node == self.NIL:
                return "Empty RB tree"
            result = "Root: " + self._node_str(node)
        else:
            indent = "|   " * (level - 1)
            # Определяем ветвь (L или R)
            if node.parent != self.NIL:
                branch = "L: " if node == node.parent.leftch else "R: "
            else:
                branch = ""
            result = f"\n{indent}{branch}{self._node_str(node)}"

        # Рекурсивно обрабатываем детей
        has_left = node.leftch != self.NIL
        has_right = node.rightch != self.NIL

        if has_left or has_right:
            if has_left:
                result += self.__str__(node.leftch, level + 1)
            else:
                indent = "|   " * level
                result += f"\n{indent}L: NIL"

            if has_right:
                result += self.__str__(node.rightch, level + 1)
            else:
                indent = "|   " * level
                result += f"\n{indent}R: NIL"

        return result

    def _node_str(self, node) -> str:
        """Переопределяем для отображения цвета"""
        if node == self.NIL:
            return "NIL"
        return str(node)

    def _create_node(self, key):
        """Создание RB узла"""
        newNode = RBNode(key)
        newNode.leftch = self.NIL
        newNode.rightch = self.NIL
        newNode.color = RED
        return newNode

    def _is_empty(self, node) -> bool:
        """Переопределяем для работы с NIL"""
        return node is None or node == self.NIL

    # Методы вращения для RB дерева
    def _left_rotate(self, x):
        """Левый поворот"""
        y = x.rightch
        x.rightch = y.leftch

        if y.leftch != self.NIL:
            y.leftch.parent = x

        y.parent = x.parent

        if x.parent == self.NIL:
            self.root = y
        elif x == x.parent.leftch:
            x.parent.leftch = y
        else:
            x.parent.rightch = y

        y.leftch = x
        x.parent = y

    def _right_rotate(self, x):
        """Правый поворот"""
        y = x.leftch
        x.leftch = y.rightch

        if y.rightch != self.NIL:
            y.rightch.parent = x

        y.parent = x.parent

        if x.parent == self.NIL:
            self.root = y
        elif x == x.parent.rightch:
            x.parent.rightch = y
        else:
            x.parent.leftch = y

        y.rightch = x
        x.parent = y

    def _fix_insert(self, z):
        """Исправление свойств RB-дерева после вставки"""
        while z.parent.color == RED:
            if z.parent == z.parent.parent.leftch:
                y = z.parent.parent.rightch  # Дядя

                if y.color == RED:
                    # Случай 1: дядя красный
                    z.parent.color = BLACK
                    y.color = BLACK
                    z.parent.parent.color = RED
                    z = z.parent.parent
                else:
                    if z == z.parent.rightch:
                        # Случай 2: z - правый ребенок
                        z = z.parent
                        self._left_rotate(z)

                    # Случай 3: z - левый ребенок
                    z.parent.color = BLACK
                    z.parent.parent.color = RED
                    self._right_rotate(z.parent.parent)
            else:
                y = z.parent.parent.leftch  # Дядя

                if y.color == RED:
                    # Случай 1: дядя красный
                    z.parent.color = BLACK
                    y.color = BLACK
                    z.parent.parent.color = RED
                    z = z.parent.parent
                else:
                    if z == z.parent.leftch:
                        # Случай 2: z - левый ребенок
                        z = z.parent
                        self._right_rotate(z)

                    # Случай 3: z - правый ребенок
                    z.parent.color = BLACK
                    z.parent.parent.color = RED
                    self._left_rotate(z.parent.parent)

            if z == self.root:
                break

        self.root.color = BLACK

    def insert(self, key):
        """Вставка нового ключа в дерево с RB балансировкой"""
        z = self._create_node(key)
        y = self.NIL
        x = self.root

        while x != self.NIL:
            y = x
            if z.key < x.key:
                x = x.leftch
            else:
                x = x.rightch

        z.parent = y

        if y == self.NIL:
            self.root = z
        elif z.key < y.key:
            y.leftch = z
        else:
            y.rightch = z

        if z.parent == self.NIL:
            z.color = BLACK
            return z

        if z.parent.parent == self.NIL:
            return z

        self._fix_insert(z)
        return z

    def _transplant(self, u, v):
        """Замена поддерева u на поддерево v"""
        if u.parent == self.NIL:
            self.root = v
        elif u == u.parent.leftch:
            u.parent.leftch = v
        else:
            u.parent.rightch = v
        v.parent = u.parent

    def _fix_delete(self, x):
        """Исправление свойств RB-дерева после удаления"""
        while x != self.root and x.color == BLACK:
            if x == x.parent.leftch:
                w = x.parent.rightch
                if w.color == RED:
                    w.color = BLACK
                    x.parent.color = RED
                    self._left_rotate(x.parent)
                    w = x.parent.rightch

                if w.leftch.color == BLACK and w.rightch.color == BLACK:
                    w.color = RED
                    x = x.parent
                else:
                    if w.rightch.color == BLACK:
                        w.leftch.color = BLACK
                        w.color = RED
                        self._right_rotate(w)
                        w = x.parent.rightch

                    w.color = x.parent.color
                    x.parent.color = BLACK
                    w.rightch.color = BLACK
                    self._left_rotate(x.parent)
                    x = self.root
            else:
                w = x.parent.leftch
                if w.color == RED:
                    w.color = BLACK
                    x.parent.color = RED
                    self._right_rotate(x.parent)
                    w = x.parent.leftch

                if w.rightch.color == BLACK and w.leftch.color == BLACK:
                    w.color = RED
                    x = x.parent
                else:
                    if w.leftch.color == BLACK:
                        w.rightch.color = BLACK
                        w.color = RED
                        self._left_rotate(w)
                        w = x.parent.leftch

                    w.color = x.parent.color
                    x.parent.color = BLACK
                    w.leftch.color = BLACK
                    self._right_rotate(x.parent)
                    x = self.root
        x.color = BLACK

    def deleteValue(self, key):
        """Удаление узла по ключу с RB балансировкой"""
        z = self.findNode(key)
        if z is None or z == self.NIL:
            return False

        y = z
        y_original_color = y.color
        if z.leftch == self.NIL:
            x = z.rightch
            self._transplant(z, z.rightch)
        elif z.rightch == self.NIL:
            x = z.leftch
            self._transplant(z, z.leftch)
        else:
            y = self._find_min_node(z.rightch)
            y_original_color = y.color
            x = y.rightch
            if y.parent == z:
                x.parent = y
            else:
                self._transplant(y, y.rightch)
                y.rightch = z.rightch
                y.rightch.parent = y

            self._transplant(z, y)
            y.leftch = z.leftch
            y.leftch.parent = y
            y.color = z.color

        if y_original_color == BLACK:
            self._fix_delete(x)

        return True

    # Методы обхода наследуются от BST и работают корректно

    # Дополнительные методы для экспериментов
    def getNodeHeight(self, node):
        """Вычисление высоты конкретного узла от листьев"""
        if node == self.NIL:
            return 0
        left_height = self.getNodeHeight(node.leftch) if node.leftch != self.NIL else 0
        right_height = self.getNodeHeight(node.rightch) if node.rightch != self.NIL else 0
        return max(left_height, right_height) + 1


# Теоретические оценки высоты для красно-черного дерева
def rb_theoretical_lower_bound(n):
    """Нижняя оценка высоты RB-дерева: log₂(n+1)"""
    if n == 0:
        return 0
    return math.log2(n + 1)


def rb_theoretical_upper_bound(n):
    """Верхняя оценка высоты RB-дерева: 2*log₂(n+1)"""
    if n == 0:
        return 0
    return 2 * math.log2(n + 1)


def experiment_random_keys():
    """Эксперимент со случайными ключами"""
    max_n = 20000
    step = 100
    n_values = []
    heights = []
    lower_bounds = []
    upper_bounds = []

    all_keys = list(range(max_n))
    random.shuffle(all_keys)

    for n in range(0, max_n + 1, step):
        n_values.append(n)

        if n == 0:
            height = 0
        else:
            tree = RBTree()
            for i in range(n):
                tree.insert(all_keys[i])
            height = tree.getheight()

        heights.append(height)
        lower_bounds.append(rb_theoretical_lower_bound(n))
        upper_bounds.append(rb_theoretical_upper_bound(n))

    return n_values, heights, lower_bounds, upper_bounds


def experiment_sorted_keys():
    """Эксперимент с монотонно возрастающими ключами"""
    max_n = 20000
    step = 100
    n_values = []
    heights = []
    lower_bounds = []
    upper_bounds = []

    for n in range(0, max_n + 1, step):
        n_values.append(n)

        if n == 0:
            height = 0
        else:
            tree = RBTree()
            for i in range(n):
                tree.insert(i)
            height = tree.getheight()

        heights.append(height)
        lower_bounds.append(rb_theoretical_lower_bound(n))
        upper_bounds.append(rb_theoretical_upper_bound(n))

    return n_values, heights, lower_bounds, upper_bounds


def plot_results():
    """Построение графиков результатов экспериментов"""
    n_rand, h_rand, lb_rand, ub_rand = experiment_random_keys()
    n_sorted, h_sorted, lb_sorted, ub_sorted = experiment_sorted_keys()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # График 1: случайные ключи
    ax1.plot(n_rand, h_rand, 'b-', label='Экспериментальная высота', linewidth=2, alpha=0.7)
    ax1.plot(n_rand, lb_rand, 'r--', label='Теоретическая нижняя оценка', linewidth=1.5)
    ax1.plot(n_rand, ub_rand, 'g--', label='Теоретическая верхняя оценка', linewidth=1.5)
    ax1.set_xlabel('Количество ключей (n)')
    ax1.set_ylabel('Высота дерева')
    ax1.set_title('Зависимость высоты RB-дерева от n\n(случайные ключи)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, max(n_rand))

    # График 2: монотонно возрастающие ключи
    ax2.plot(n_sorted, h_sorted, 'b-', label='Экспериментальная высота', linewidth=2, alpha=0.7)
    ax2.plot(n_sorted, lb_sorted, 'r--', label='Теоретическая нижняя оценка', linewidth=1.5)
    ax2.plot(n_sorted, ub_sorted, 'g--', label='Теоретическая верхняя оценка', linewidth=1.5)
    ax2.set_xlabel('Количество ключей (n)')
    ax2.set_ylabel('Высота дерева')
    ax2.set_title('Зависимость высоты RB-дерева от n\n(монотонно возрастающие ключи)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, max(n_sorted))

    plt.tight_layout()
    plt.show()


# Основная программа
if __name__ == "__main__":
    print("RB дерево после вставки 20 элементов:\n")

    rb_tree = RBTree()
    elements = random.sample(range(-10, 26), 20)

    for elem in elements:
        rb_tree.insert(elem)

    print(rb_tree)
    print(f"\nВысота = {rb_tree.getheight()}")

    print("\n" + "=" * 50 + "\n")

    # Все методы обхода работают через наследование!
    print("Различные обходы дерева:")
    print(f"Центрированный обход = {rb_tree.inOrderTraversal()}")
    print(f"Прямой обход = {rb_tree.preOrderTraversal()}")
    print(f"Обратный обход = {rb_tree.postOrderTraversal()}")
    print(f"По уровням/в ширину = {rb_tree.levelOrderTraversal()}")

    # Методы поиска тоже наследуются
    min_node = rb_tree.findMin()
    max_node = rb_tree.findMax()
    print(f"\nМинимум = {min_node.key if min_node != rb_tree.NIL else 'None'}")
    print(f"Максимум = {max_node.key if max_node != rb_tree.NIL else 'None'}")

    # Поиск случайного узла
    random_key = random.choice(elements)
    found_node = rb_tree.findNode(random_key)
    if found_node and found_node != rb_tree.NIL:
        print(f"\nПоиск узла {random_key}:")
        print(f"Значение узла = {found_node.key};")
        print(f"Родитель: {found_node.parent.key if found_node.parent != rb_tree.NIL else 'None'},")
        print(f"Левый потомок: {found_node.leftch.key if found_node.leftch != rb_tree.NIL else 'None'},")
        print(f"Правый потомок: {found_node.rightch.key if found_node.rightch != rb_tree.NIL else 'None'},")
        print(f"Цвет узла: {found_node.color}.")

    # Проверка на пустоту
    print(f"\nДерево пустое? {rb_tree.isEmpty()}")

    print("\n" + "=" * 50 + "\n")

    print("Балансировка после вставки 3 случайных элементов:\n")
    random_elements = random.sample(range(-50, 50), 1)
    print(f"Вставляем 1 случайный элемент: {random_elements}")

    for elem in random_elements:
        rb_tree.insert(elem)
        print(f"\nПосле вставки {elem}:")
        print(rb_tree)
        print(f"Высота после вставки = {rb_tree.getheight()}")

    print("\n" + "=" * 50 + "\n")

    print("RB дерево после удаления 3 элементов:\n")
    all_elements = elements + random_elements
    to_delete = random.sample(all_elements, 3)
    print(f"Удаляем 3 элемента: {to_delete}")

    for elem in to_delete:
        success = rb_tree.deleteValue(elem)

    print()
    print(rb_tree)
    print(f"\nВысота дерева после удаления = {rb_tree.getheight()}\n")

    print("=" * 60)
    print(f"\nСтроим графики...")
    plot_results()