class PromptManager:
    @staticmethod
    def get_system_prompt(is_chunk=False, past_context=""):
        base = "You are a senior AI DevOps assistant. Analyze the provided log file line-by-line.\n"
        
        if past_context:
            base += f"\n--- Historical Context (Past issues that might be related) ---\n{past_context}\n--------------------------------------------------------\n"
            
        if is_chunk:
            base += "\nAnalyze the provided log file chunk. Create a structured Markdown table/matrix highlighting each error line. Columns: | Line/Log Entry | Root Cause | Proposed Fix |"
            base += "\nDo not generate a final executive summary, just the table."
        else:
            base += "\nCreate a strict Markdown (.md) report containing a comparison matrix/table identifying issues. Columns: | Log Entry | Root Cause | Proposed Fix |"
            
        return base
        
    @staticmethod
    def get_user_prompt(filename, content, chunk_info=""):
        prompt = f"Log filename: {filename}\n"
        if chunk_info:
            prompt += f"{chunk_info}\n"
        prompt += f"\nContent to analyze:\n{content}"
        return prompt
