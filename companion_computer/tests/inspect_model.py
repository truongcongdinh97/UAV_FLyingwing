import sys
import os
import numpy as np

# Try to import tflite
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    try:
        import tensorflow.lite as tflite
    except ImportError:
        print("Error: TensorFlow Lite not installed")
        sys.exit(1)

def inspect_model(model_path):
    print(f"Inspecting model: {model_path}")
    
    if not os.path.exists(model_path):
        print("Error: Model file not found!")
        return

    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    print("\n--- INPUTS ---")
    for i, detail in enumerate(input_details):
        print(f"Input {i}:")
        print(f"  Name: {detail['name']}")
        print(f"  Shape: {detail['shape']}")
        print(f"  Type: {detail['dtype']}")
        print(f"  Index: {detail['index']}")

    print("\n--- OUTPUTS ---")
    for i, detail in enumerate(output_details):
        print(f"Output {i}:")
        print(f"  Name: {detail['name']}")
        print(f"  Shape: {detail['shape']}")
        print(f"  Type: {detail['dtype']}")
        print(f"  Index: {detail['index']}")

if __name__ == "__main__":
    # Path from your log
    model_path = r"H:\VSCode\Flying_Wing_UAV\companion_computer\models\mobilenet_ssd_v2.tflite"
    inspect_model(model_path)
