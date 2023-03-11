#  This code has been taken from https://towardsdatascience.com/python-linked-lists-c3622205da81

class Node:
    def __init__(self, value, next_node=None, prev_node=None):
        self.value = value
        self.next = next_node
        self.prev = prev_node

    def __str__(self):
        return str(self.value)


class LinkedList:
    def __init__(self, values=None):
        self.head = None
        self.tail = None
        if values is not None:
            self.add_multiple_nodes(values)

    def __str__(self):
        return ' -> '.join([str(node) for node in self])

    def __len__(self):
        count = 0
        node = self.head
        while node:
            count += 1
            node = node.next
        return count

    def __iter__(self):
        current = self.head
        while current:
            yield current
            current = current.next

    @property
    def values(self):
        return [node.value for node in self]

    def add_node(self, value):
        if self.head is None:
            self.tail = self.head = Node(value)
        else:
            self.tail.next = Node(value)
            self.tail.next.prev = self.tail
            self.tail = self.tail.next
        return self.tail

    def add_multiple_nodes(self, values):
        for value in values:
            self.add_node(value)

    def remove_head(self):
        if self.head is not None:
            node = self.head
            if self.tail == node:
                self.head = None
                self.tail = None
            else:
                node.next.prev = None
                self.head = node.next
            return node.value

    def remove(self, node: Node):
        if node is None:
            return
        if self.head == node:
            return self.remove_head()
        if self.tail == node:
            self.tail = node.prev
        else:
            node.next.prev = node.prev
        node.prev.next = node.next
        return node.value
