import os

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

class PromptManager:
    @staticmethod
    def get_system_prompt(is_chunk=False, past_context=""):
        filename = "chunk_system_prompt.txt" if is_chunk else "system_prompt.txt"
        file_path = os.path.join(PROMPTS_DIR, filename)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                prompt = f.read()
        except FileNotFoundError:
            # Fallback if files are missing
            prompt = "You are a senior AI DevOps assistant. Analyze logs line-by-line. Output a Markdown table with columns: | Log Entry | Root Cause | Proposed Fix |\n{past_context}"
            
        context_str = ""
        if past_context:
            context_str = f"\n--- Historical Context (Past related issues) ---\n{past_context}\n--------------------------------------------------------\n"
            
        return prompt.replace("{past_context}", context_str)
        
    @staticmethod
    def get_user_prompt(filename, content, chunk_info=""):
        prompt = f"Log filename: {filename}\n"
        if chunk_info:
            prompt += f"{chunk_info}\n"
        prompt += f"\nContent to analyze:\n{content}"
        return prompt
