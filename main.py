from src import image_processing

ip = image_processing.image_processing(resolution=80)

matrix1, timestamp1 = ip.image_to_matrix("input_examples/penrose.png")
matrix2, timestamp2 = ip.person_to_matrix("input_examples/person.png")

print(matrix1)
print(timestamp1)
print()
print(matrix2)
print(timestamp2)