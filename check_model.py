import torch

model_path = 'best_skin_model.pth'

try:
    # Attempt to load the file
    data = torch.load(model_path, map_location='cpu')
    
    print("\n" + "="*30)
    print(f"File: {model_path}")
    print(f"Data Type: {type(data)}")
    
    if isinstance(data, dict):
        print("Result: This is a STATE DICT (Weights only).")
        print(f"Keys found: {list(data.keys())[:5]}... (Total keys: {len(data)})")
    else:
        print("Result: This is a FULL MODEL object.")
        print(f"Model Class: {data.__class__.__name__}")
    print("="*30 + "\n")

except Exception as e:
    print(f"\nError loading file: {e}")
    print("If you see 'PytorchStreamReader' error here, the file is likely a corrupted TorchScript or a different format.")