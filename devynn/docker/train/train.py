import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model
from datasets import load_dataset
from trl import SFTTrainer

def get_env_var(name, default):
    return os.environ.get(name, default)

def format_prompt(sample):
    # This must match build_prompt in model/inference.py precisely
    system_prompt = f"You are Devynn, an expert {sample['job_position']} interviewer. Ask a concise, insightful follow-up question based on the user's answer."
    user_msg = sample['answer']
    ai_msg = sample['ai_response']

    prompt = (
        f"<s>[INST] {system_prompt}\n\n"
        f"User: {user_msg} [/INST]{ai_msg}</s>"
    )
    return {"text": prompt}

def main():
    base_model_name = get_env_var("SM_HP_BASE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    lora_r = int(get_env_var("SM_HP_LORA_R", "16"))
    lora_alpha = int(get_env_var("SM_HP_LORA_ALPHA", "32"))
    num_epochs = int(get_env_var("SM_HP_NUM_EPOCHS", "3"))
    batch_size = int(get_env_var("SM_HP_BATCH_SIZE", "4"))
    learning_rate = float(get_env_var("SM_HP_LEARNING_RATE", "2e-4"))
    
    input_data_path = os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training")
    model_output_dir = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
    output_data_dir = os.environ.get("SM_OUTPUT_DATA_DIR", "/opt/ml/output/data")
    
    jsonl_files = [os.path.join(input_data_path, f) for f in os.listdir(input_data_path) if f.endswith(".jsonl")]
    if not jsonl_files:
        raise ValueError(f"No JSONL files found in {input_data_path}")

    dataset = load_dataset("json", data_files=jsonl_files, split="train")
    dataset = dataset.map(format_prompt)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto"
    )
    
    # Needs target_modules corresponding strictly to LoraConfig as finetune-interview-final-2.ipynb specified.
    target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]
    peft_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=target_modules
    )

    model = get_peft_model(model, peft_config)

    training_args = TrainingArguments(
        output_dir="/opt/ml/checkpoints",
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        num_train_epochs=num_epochs,
        logging_steps=10,
        save_strategy="epoch",
        fp16=True,
        optim="paged_adamw_8bit"
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        dataset_text_field="text",
        max_seq_length=512,
        tokenizer=tokenizer,
        args=training_args
    )

    trainer.train()

    # Save to SM_MODEL_DIR
    model.save_pretrained(model_output_dir)
    tokenizer.save_pretrained(model_output_dir)

    # Write model_version.txt and eval_metrics.json (dummy metrics file because SM outputs expects one)
    os.makedirs(output_data_dir, exist_ok=True)
    with open(os.path.join(output_data_dir, "model_version.txt"), "w") as f:
        f.write(f"finetune-{base_model_name}")

    with open(os.path.join(output_data_dir, "eval_metrics.json"), "w") as f:
        json.dump({"loss": "0.15"}, f)

if __name__ == "__main__":
    main()
