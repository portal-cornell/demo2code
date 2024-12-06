"""
This module acts as a wrapper for OpenAI's chat API.
"""
import os
import time

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


def call_openai_api(main_prompt, raw_examples_list, user_query, stop_list=[], temperature=0.7, max_tokens=2000, gpt_model="gpt-3.5-turbo"):
    """
    Parameters:
        main_prompt (str) - see below for an example of the prompt
            *   system message
            *   main prompt
            *   (optional) example user query and responses
        user_query (str) - user's input
        has_examples (bool) - True if your overall prompt contains example user query and responses
        temperature (float) - how creative LLMs are
        stop_list (list of str) - a list of stop keywords
        max_tokens (int) - maximum tokens LLM should output
        gpt_model (str) - gpt model names
            *   regular gpt 3.5 models: "gpt-3.5-turbo"
            *   16k context length gpt 3.5 models: "gpt-3.5-turbo-16k"
    """
    max_tokens_in_use = max_tokens

    # parse the overall prompt into sys_msg and prompt
    sys_msg, _, prompt = main_prompt.partition("<end_of_system_message>")
    sys_msg = sys_msg.strip("\n")
    prompt = prompt.strip("\n")

    example_list = []
    if raw_examples_list:
        for example_text in raw_examples_list:
            example_user_query, _, example_response = example_text.strip("\n").partition("<end_of_example_user_query>")
            example_list.append((example_user_query.strip("\n"), example_response.strip("\n")))

    messages_to_gpt = [{"role": "system", "content": sys_msg},
                        {"role": "user", "content": prompt}]

    if example_list:
        for example_user_query, example_response in example_list:
            messages_to_gpt.append({"role": "user", "content": example_user_query})
            messages_to_gpt.append({"role": "assistant", "content": example_response})

    messages_to_gpt.append({"role": "user", "content": user_query.strip().strip("\n")})

    client = openai.OpenAI()

    while True:
        try:
            response = client.chat.completions.create(
                model=gpt_model,
                messages=messages_to_gpt,
                temperature=temperature,
                max_tokens=max_tokens_in_use,
                stop = stop_list if stop_list else None
            )
            print(response.usage)

            output_str = response.choices[0].message.content.strip()    

            return output_str
        except openai.AuthenticationError as e:
            print(e)
            return None
        except openai.RateLimitError as e:
            print(e)
            print("Sleeping for 5 seconds...")
            time.sleep(5)
        except openai.BadRequestError as e:
            print(e)
            print(f"Trying with max-token={max_tokens_in_use} to max-token={max_tokens_in_use - 25}")
            max_tokens_in_use -= 25
        except Exception as e:
            print(e)
            print("Sleeping for 5 seconds...")


    
