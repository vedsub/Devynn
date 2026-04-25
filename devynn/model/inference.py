import os
import torch

def generate_output(transcript: str, domain: str, model, tokenizer):
    if os.environ.get("MODEL_PATH") == "mock":
        return f"Mock follow-up question for {domain}.\nGrammar:\nMock grammar note."
        
    prompt = (
        f"You are now conducting an interview for the {domain} role.\n"
        f"The candidate said: {transcript}\n"
        f"Formulate a thoughtful follow-up question."
    )
    
    max_new_tokens = 200
    model_input = tokenizer(prompt, return_tensors="pt")

    model.eval()
    with torch.no_grad():
        output = model.generate(**model_input, max_new_tokens=max_new_tokens)

    decoded_output = tokenizer.decode(output[0], skip_special_tokens=True)
    return decoded_output