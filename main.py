from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")
response = llm.invoke("can you give me a summary of chapter 1 of project hail mary")
print(response.content)
