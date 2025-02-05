import re
from typing import List
from peft import PeftModel, PeftConfig
from transformers import AutoModelForCausalLM, AutoTokenizer


class Summarizer:
    """A class for summarizing a group of tweets using the LLaMa2 model."""

    def __init__(self):
        """Initialize the summarizer and load the necessary models and tokenizers."""
        peft_model_id = "TANUKImao/LLaMa2TS-0.1.0"
        config = PeftConfig.from_pretrained(peft_model_id)
        model = AutoModelForCausalLM.from_pretrained(
            config.base_model_name_or_path,
            return_dict=True,
            load_in_8bit=True,
            device_map='auto'
        )

        self.model = PeftModel.from_pretrained(model, peft_model_id)
        self.tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path, use_fast=True)
        self.tokenizer.pad_token_id = self.tokenizer.eos_token_id  # set pad token to eos token

    def construct_corpus(self, corpus: List[str]) -> str:
        """Construct the corpus in the format expected by the LLaMa2 model."""
        tweets = ''
        for i, text in enumerate(corpus, 1):
            tweets += f"{i}-[{text}] "
        prompt = (f"<s>[INST] <<SYS>>\n"
                  f"I would like you to help me by summarizing a group of tweets, delimited by triple backticks,"
                  f" and each tweet is labeled by a number in a given format: number-[tweet]."
                  f" Give me a comprehensive summary in a concise paragraph."
                  f" As you generate each sentence, provide the identifying number of tweets on which that sentence is based:"
                  f"\n<</SYS>>\n``` {tweets} ``` \n [/INST] \n")
        return prompt

    def llm_summarize(self, corpus: List[str]) -> str:
        """Summarize a corpus of text using the LLaMa2 Large Language Model."""
        prompt = self.construct_corpus(corpus)
        inputs = self.tokenizer(prompt, return_tensors="pt").to('cuda')
        sequences = self.model.generate(
            **inputs,
            max_new_tokens=1000,
            do_sample=True,
            top_k=100,
            pad_token_id=self.tokenizer.eos_token_id
        )
        decoded_sequence = self.tokenizer.decode(sequences[0])
        output = re.search(r'\n \[/INST\] \n(.*?) </s>', decoded_sequence, re.DOTALL)
    
        if output:
            return output.group(1).strip()
        else:
            return "No summary generated."