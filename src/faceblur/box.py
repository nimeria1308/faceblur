# Copyright (C) 2025, Simona Dimitrova


class Box:
    def __init__(self, top, right, bottom, left):
        if left > right:
            raise ValueError(f"left={left} > right={right}")

        # The coordinate are inverted on Y
        if top > bottom:
            raise ValueError(f"top={top} > bottom={bottom}")

        self.top = top
        self.right = right
        self.bottom = bottom
        self.left = left

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top

    def intersect(self, other):
        # Calculate the intersection coordinates
        intersection_top = max(self.top, other.top)
        intersection_right = min(self.right, other.right)
        intersection_bottom = min(self.bottom, other.bottom)
        intersection_left = max(self.left, other.left)

        # Check if there is an intersection
        if intersection_top <= intersection_bottom and intersection_left <= intersection_right:
            return Box(intersection_top, intersection_right, intersection_bottom, intersection_left)
        else:
            # No intersection
            return None

    def union(self, other):
        # Calculate the union coordinates
        union_top = min(self.top, other.top)
        union_right = max(self.right, other.right)
        union_bottom = max(self.bottom, other.bottom)
        union_left = min(self.left, other.left)
        return Box(union_top, union_right, union_bottom, union_left)

    def area(self):
        return (self.bottom - self.top + 1) * (self.right - self.left + 1)

    def normalise(self, width, height):
        return Box(self.top / height, self.right / width, self.bottom / height, self.left / width)

    def denormalise(self, width, height):
        box = Box(
            int(self.top * height),
            int(self.right * width),
            int(self.bottom * height),
            int(self.left * width))

        # Make sure the face is within the image
        max_box = Box(0, width - 1, height - 1, 0)

        return box.intersect(max_box)

    def __repr__(self):
        return f"Box(top={self.top}, right={self.right}, bottom={self.bottom}, left={self.left})"

    def __eq__(self, other):
        return self.top == other.top and self.right == other.right and self.bottom == other.bottom and self.left == other.left

    def intersection_over_union(self, other):
        intersection = self.intersect(other)
        if not intersection:
            # Do not intersect
            return 0

        intersection_area = intersection.area()

        # area of the union
        union_area = self.area() + other.area() - intersection_area

        # intersection over union
        return intersection_area / union_area

    def to_json(self):
        return vars(self)
