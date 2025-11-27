import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SYSTEM_PROMPT = (
    "<system\n"
    "Ты технолог-консультант на производстве АО СПЛАВ, ты консультируешь работников на производстве.\n"
    "Используя только предоставленный контекст, дай точный, развернутый и подробный ответ на вопрос пользователя.\n"
    "Вся необоходимая для ответа информация содержится в предоставленном контекстe. Меньше размышляй.\n"
    "Ответ должен быть информативным. Если в контексте информации нет, то говори: 'Я не нашел информацию по вашему запросу'\n"
    ">\nuser\n"
)

def load_llm(model_path: str):
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    model.to(DEVICE)
    model.eval()
    return tokenizer, model
def generate_answer(
        tokenizer,
        model,
        history: list,
        question: str,
        context: str,
        system_prompt: str = SYSTEM_PROMPT
    ) -> str:

    chat_messages = []

    # SYSTEM
    chat_messages.append({"role": "system", "content": system_prompt})

    # HISTORY
    for role, msg in history:
        if role == "user":
            chat_messages.append({"role": "user", "content": msg})
        else:
            chat_messages.append({"role": "assistant", "content": msg})

    # CONTEXT + QUESTION
    chat_messages.append({
        "role": "user",
        "content": (
            f"Контекст:\n{context}\n\n"
            f"Вопрос: {question}"
        )
    })

    # APPLY TEMPLATE
    prompt = tokenizer.apply_chat_template(
        chat_messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)

    gen_config = GenerationConfig(
        max_new_tokens=1000,
        temperature=0.2,
        top_p=0.9,
        do_sample=False,
        eos_token_id=tokenizer.eos_token_id
    )

    with torch.no_grad():
        output = model.generate(**inputs, generation_config=gen_config)

    decoded = tokenizer.decode(output[0], skip_special_tokens=True)
    return decoded
