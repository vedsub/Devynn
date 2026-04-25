import os
import torch

def build_prompt(transcript: str, domain: str) -> str:
    system_prompt = f"You are Devynn, an expert {domain} interviewer. Ask a concise, insightful follow-up question based on the user's answer."
    return f"<s>[INST] {system_prompt}\n\nUser: {transcript} [/INST]"

def generate_output(transcript: str, domain: str, model, tokenizer):
    if os.environ.get("MODEL_PATH") == "mock":
        return f"Mock follow-up question for {domain}.\nGrammar:\nMock grammar note."
        
    prompt = build_prompt(transcript, domain)
    
    max_new_tokens = 200
    model_input = tokenizer(prompt, return_tensors="pt")

    model.eval()
    with torch.no_grad():
        output = model.generate(**model_input, max_new_tokens=max_new_tokens)

    decoded_output = tokenizer.decode(output[0], skip_special_tokens=True)
    return decoded_output