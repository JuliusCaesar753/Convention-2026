from src import image_processing

ip = image_processing.image_processing(resolution=200)

matrix, timestamp = ip.image_to_matrix("input_examples/Discord.png")

print(matrix, timestamp)