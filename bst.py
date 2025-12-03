# Класс узла бинарного дерева
class Node:
    def __init__(self, key):
        self.key = key  # Значение узла
        self.leftch = None  # Левый потомок
        self.rightch = None  # Правый потомок
        self.parent = None  # Родительский узел

    def __str__(self) -> str:
        return str(self.key)  # Строковое представление


# Класс бинарного дерева поиска (базовый)
class BST:
    def __init__(self):
        self.root = self._create_empty_child()  # Инициализация корня
        self.NIL = None  # Для совместимости с RB (в BST NIL = None)

    def __str__(self, node=None, level=1) -> str:
        """Универсальный вывод дерева с отступами"""
        # Начало рекурсии
        if node is None:
            node = self.root
            if self._is_empty(node):
                return "Empty tree"
            result = "Root: " + self._node_str(node)
        else:
            indent = "|   " * (level - 1)
            branch = "L: " if node == node.parent.leftch else "R: "
            result = f"\n{indent}{branch}{self._node_str(node)}"

        # Рекурсивно обрабатываем детей
        if not self._is_empty(node.leftch) or not self._is_empty(node.rightch):
            if not self._is_empty(node.leftch):
                result += self.__str__(node.leftch, level + 1)
            else:
                indent = "|   " * level
                result += f"\n{indent}L: None"

            if not self._is_empty(node.rightch):
                result += self.__str__(node.rightch, level + 1)
            else:
                indent = "|   " * level
                result += f"\n{indent}R: None"

        return result

    def _node_str(self, node) -> str:
        """Виртуальный метод для строкового представления узла"""
        return str(node)

    def _create_node(self, key):
        """Виртуальный метод создания узла"""
        return Node(key)

    def _is_empty(self, node) -> bool:
        """Проверка на пустой узел (совместимость с NIL)"""
        return node is None or node == self.NIL

    def _create_empty_child(self):
        """Создание пустой ссылки"""
        return None

    def _copy_values(self, dest, src):
        """Копирование значений между узлами"""
        dest.key = src.key

    def insert(self, key):
        """Базовая вставка без балансировки"""
        current = self.root
        newNode = self._create_node(key)

        if self._is_empty(current):
            # Дерево пустое
            self.root = newNode
        else:
            parentNode = None
            # Поиск места для вставки
            while not self._is_empty(current):
                parentNode = current
                if current.key < key:
                    current = current.rightch
                else:
                    current = current.leftch

            # Установка связей
            newNode.parent = parentNode
            if parentNode.key < key:
                parentNode.rightch = newNode
            else:
                parentNode.leftch = newNode
        return newNode

    def findNode(self, key):
        """Поиск узла по ключу"""
        node = self.root
        while not self._is_empty(node):
            if node.key == key:
                return node
            if node.key < key:
                node = node.rightch
            else:
                node = node.leftch
        return None

    def findMin(self):
        """Поиск минимального элемента"""
        if self._is_empty(self.root):
            return self.NIL
        node = self.root
        while not self._is_empty(node.leftch):
            node = node.leftch
        return node

    def findMax(self):
        """Поиск максимального элемента"""
        if self._is_empty(self.root):
            return self.NIL
        node = self.root
        while not self._is_empty(node.rightch):
            node = node.rightch
        return node

    def _find_min_node(self, node):
        """Найти узел с минимальным значением в поддереве"""
        current = node
        while not self._is_empty(current.leftch):
            current = current.leftch
        return current

    def deleteValue(self, key):
        """Удаление узла по ключу"""
        delNode = self.findNode(key)
        if delNode is not None:
            return self.delete_node(delNode)
        return None

    def delete_node(self, delNode):
        """Базовая реализация удаления узла"""
        if self._is_empty(delNode):
            return None

        parentNode = delNode.parent
        result = None

        # Случай 1: нет потомков
        if self._is_empty(delNode.leftch) and self._is_empty(delNode.rightch):
            if not self._is_empty(parentNode):
                result = self._create_empty_child()
                if parentNode.key < delNode.key:
                    parentNode.rightch = result
                else:
                    parentNode.leftch = result
            else:
                result = self._create_empty_child()
                self.root = result

        # Случай 2: только левый потомок
        elif not self._is_empty(delNode.leftch) and self._is_empty(delNode.rightch):
            result = delNode.leftch
            if result:
                result.parent = parentNode
            if self._is_empty(parentNode):
                self.root = result
            elif parentNode.leftch == delNode:
                parentNode.leftch = result
            else:
                parentNode.rightch = result

        # Случай 3: только правый потомок
        elif self._is_empty(delNode.leftch) and not self._is_empty(delNode.rightch):
            result = delNode.rightch
            if result:
                result.parent = parentNode
            if self._is_empty(parentNode):
                self.root = result
            elif parentNode.leftch == delNode:
                parentNode.leftch = result
            else:
                parentNode.rightch = result

        # Случай 4: два потомка
        else:
            # Находим преемника
            successor = self._find_min_node(delNode.rightch)
            self._copy_values(delNode, successor)
            result = self.delete_node(successor)

        return result

    def getheight(self, node=None) -> int:
        """Вычисление высоты дерева"""
        if node is None:
            node = self.root
            if self._is_empty(node):
                return 0
        if self._is_empty(node):
            return 0
        left_height = self.getheight(node.leftch) if not self._is_empty(node.leftch) else 0
        right_height = self.getheight(node.rightch) if not self._is_empty(node.rightch) else 0
        return max(left_height, right_height) + 1

    def inOrderTraversal(self, node=None):
        """Симметричный обход (левый, корень, правый)"""
        if node is None:
            node = self.root
        if self._is_empty(node):
            return []

        result = []
        if not self._is_empty(node.leftch):
            result.extend(self.inOrderTraversal(node.leftch))
        result.append(node.key)
        if not self._is_empty(node.rightch):
            result.extend(self.inOrderTraversal(node.rightch))
        return result

    def preOrderTraversal(self, node=None):
        """Прямой обход (корень, левый, правый)"""
        if node is None:
            node = self.root
        if self._is_empty(node):
            return []

        result = [node.key]
        if not self._is_empty(node.leftch):
            result.extend(self.preOrderTraversal(node.leftch))
        if not self._is_empty(node.rightch):
            result.extend(self.preOrderTraversal(node.rightch))
        return result

    def postOrderTraversal(self, node=None):
        """Обратный обход (левый, правый, корень)"""
        if node is None:
            node = self.root
        if self._is_empty(node):
            return []

        result = []
        if not self._is_empty(node.leftch):
            result.extend(self.postOrderTraversal(node.leftch))
        if not self._is_empty(node.rightch):
            result.extend(self.postOrderTraversal(node.rightch))
        result.append(node.key)
        return result

    def levelOrderTraversal(self):
        """Обход по уровням (ширина)"""
        from collections import deque

        if self._is_empty(self.root):
            return []

        result = []
        queue = deque([self.root])

        while queue:
            node = queue.popleft()
            if not self._is_empty(node):
                result.append(node.key)
                if not self._is_empty(node.leftch):
                    queue.append(node.leftch)
                if not self._is_empty(node.rightch):
                    queue.append(node.rightch)
        return result

    def isEmpty(self):
        """Проверка на пустое дерево"""
        return self._is_empty(self.root)


if __name__ == "__main__":
    # Тестирование базового BST
    Tree = BST()
    import random

    unique_random_numbers = random.sample(range(-10, 26), 20)

    for n in unique_random_numbers:
        Tree.insert(n)

    print("BST дерево после вставки 20 элементов:")
    print(Tree)
    print(f"Высота дерева = {Tree.getheight()}")

    # Обходы
    print("Центрированный обход =", Tree.inOrderTraversal())
    print("Прямой обход =", Tree.preOrderTraversal())
    print("Обратный обход =", Tree.postOrderTraversal())
    print("По уровням/в ширину =", Tree.levelOrderTraversal())
    min_node = Tree.findMin()
    max_node = Tree.findMax()
    print(f"\nМинимум = {min_node.key if min_node != Tree.NIL else 'None'}")
    print(f"Максимум = {max_node.key if max_node != Tree.NIL else 'None'}")
    # Поиск случайного узла
    random_key = random.choice(unique_random_numbers)
    found_node = Tree.findNode(random_key)
    if found_node and found_node != Tree.NIL:
        print(f"\nПоиск узла {random_key}:")
        print(f"Значение узла = {found_node.key};")
        print(f"Родитель: {found_node.parent.key if found_node.parent != Tree.NIL else 'None'},")
        print(f"Левый потомок: {found_node.leftch.key if found_node.leftch != Tree.NIL else 'None'},")
        print(f"Правый потомок: {found_node.rightch.key if found_node.rightch != Tree.NIL else 'None'},")

    # Проверка на пустоту
    print(f"\nДерево пустое? {Tree.isEmpty()}")
    print("=" * 60)
    deleted_nodes = random.sample(unique_random_numbers, 3)
    for key in deleted_nodes:
        Tree.deleteValue(key)
    print(f"Удаляем 3 элемента: {deleted_nodes}\n")
    print(Tree)

    print(f"\nВысота дерева после удаления = {Tree.getheight()}\n")

    print("=" * 60)
    print()
    print(f"Строим график...")
    # построение графика h(n)
    import matplotlib.pyplot as plt

    x = []
    y = []
    Tree = BST()
    number_of_elements = 10000
    unique_random_numbers = random.sample(range(number_of_elements), number_of_elements)
    for n in range(number_of_elements):
        x.append(n)
        Tree.insert(unique_random_numbers[n])
        y.append(Tree.getheight())
    plt.plot(x, y, label="h(n)")
    plt.xlabel("n")
    plt.ylabel("h")
    plt.legend()
    plt.title("Зависимость высоты h от количества элементов n\nв BST (элементы генерируются случайным образом)")
    plt.show()
