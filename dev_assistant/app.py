import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Initialize components
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

parser = StrOutputParser()

vector_store = PineconeVectorStore(
    index_name="creditchek-dev-assistant",
    embedding=embeddings,
    pinecone_api_key=os.getenv("PINECONE_API_KEY")
)

retriever = vector_store.as_retriever()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Enhanced prompt template with memory
prompt = PromptTemplate.from_template("""You're a  GenAI developer assistant bot  for CreditChek APIs , called "Mark Musk".
     Also ensure to always introduce yourself when asked first asked a question. Always respond politely and professionally.\
    Generate code that strictly follows CreditChek documentation and best practices.
    
    Current API version: 2.3
    Authentication: Bearer token
    Base URL: https://api.creditchek.africa/v2
    
    Follow these rules:
    1. Always use secure practices (env variables for secrets)
    2. Include error handling
    3. Add relevant comments
    4. Maintain conversation context
      Context: {context} Question: {question}""")
prompt.format(context="Here is some context", question="Here is a question")

# Create conversational chain
chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | parser)

def chat_interface(question):
    result =chain.invoke(question)
    return result
# Example conversation
if __name__ == "__main__":
    print(chat_interface("How to authenticate with the CreditChek API in GoLang?"))