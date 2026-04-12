# create_space_files.py
from huggingface_hub import HfApi
from dotenv import load_dotenv
import os

load_dotenv()
HF_TOKEN   = os.getenv("HUGGINGFACEHUB_API_TOKEN")
api        = HfApi(token=HF_TOKEN)
SPACE_REPO = "rohannsinghal/skin-master-api"

APP_PY = """\
import torch
import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL   = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_REPO = "rohannsinghal/skin-master-lora"

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_REPO)

print("Loading base model...")
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype = torch.float32,
    device_map  = "cpu",
)

print("Merging LoRA adapter...")
model = PeftModel.from_pretrained(base_model, ADAPTER_REPO)
model = model.merge_and_unload()
model.eval()
print("Skin Master ready")


def ask_skin_master(query: str) -> str:
    if not query or not query.strip():
        return "Please enter a skincare question."

    prompt = (
        "<|im_start|>user\\n"
        + query.strip()
        + "<|im_end|>\\n<|im_start|>assistant\\n"
    )

    inputs = tokenizer(prompt, return_tensors="pt")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens     = 250,
            temperature        = 0.1,
            do_sample          = True,
            repetition_penalty = 1.1,
            eos_token_id       = tokenizer.eos_token_id,
            pad_token_id       = tokenizer.eos_token_id,
        )

    generated = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(generated, skip_special_tokens=True)


# api_name="/predict" is REQUIRED in Gradio 5.x to expose the REST endpoint
with gr.Blocks() as demo:
    gr.Markdown("# Skin Master - Dermatology Expert")
    gr.Markdown("Fine-tuned Qwen2.5-3B on medical and conversational skincare data.")

    with gr.Row():
        inp = gr.Textbox(
            label       = "Your Skincare Question",
            placeholder = "e.g. What causes cystic acne?",
            lines       = 3,
        )
    with gr.Row():
        btn = gr.Button("Ask Skin Master", variant="primary")
    with gr.Row():
        out = gr.Textbox(
            label = "Skin Master Response",
            lines = 8,
        )

    gr.Examples(
        examples = [
            ["What is the first-line treatment for mild acne vulgaris?"],
            ["Can I use niacinamide and vitamin C together?"],
            ["Build me a simple AM routine for combination skin."],
            ["What causes rosacea and what are common triggers?"],
        ],
        inputs = inp,
    )

    # api_name makes this callable at /call/ask — required for Gradio 5.x API
    btn.click(
        fn       = ask_skin_master,
        inputs   = inp,
        outputs  = out,
        api_name = "ask",
    )

demo.launch()
"""

REQUIREMENTS_TXT = """\
transformers>=4.40.0
peft>=0.10.0
torch>=2.0.0
accelerate>=0.29.0
gradio>=4.0.0
"""

print("Uploading app.py...")
api.upload_file(
    path_or_fileobj = APP_PY.encode("utf-8"),
    path_in_repo    = "app.py",
    repo_id         = SPACE_REPO,
    repo_type       = "space",
    commit_message  = "Fix: use gr.Blocks with explicit api_name for Gradio 5.x",
)

print("Uploading requirements.txt...")
api.upload_file(
    path_or_fileobj = REQUIREMENTS_TXT.encode("utf-8"),
    path_in_repo    = "requirements.txt",
    repo_id         = SPACE_REPO,
    repo_type       = "space",
    commit_message  = "requirements.txt",
)

print("Done — Space rebuilding.")
print(f"Logs: https://huggingface.co/spaces/{SPACE_REPO}")