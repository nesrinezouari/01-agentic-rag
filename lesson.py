from gitsource import GithubRepositoryDataReader
from minsearch import Index
from dotenv import load_dotenv
import os                   
from openai import OpenAI    
from toyaikit.llm import OpenAIClient
from toyaikit.tools import Tools 
from toyaikit.chat import IPythonChatInterface
from toyaikit.chat.runners import OpenAIResponsesRunner, DisplayingRunnerCallback                                                                                                                                                                             
from pathlib import Path
from rag_helper import RAGBase
from gitsource import chunk_documents
instructions = """
You're a course teaching assistant. Answer the student's question using the search tool. Make multiple searches with different keywords before answering.
""".strip()
reader = GithubRepositoryDataReader(
    repo_owner="DataTalksClub",
    repo_name="llm-zoomcamp",
    commit_id="8c1834d",
    allowed_extensions={"md"},
    filename_filter=lambda path: "/lessons/" in path,
)

files = reader.read()
documents = []
number_lessons=len(files)
for file in files:
    doc = file.parse()
    documents.append(doc)
print ("How many lesson pages are in the dataset?")
print("The number of lessons is {first}".format(first=number_lessons)) 
question ='How does the agentic loop keep calling the model until it stops?'


index = Index(
    text_fields=["content"],
    keyword_fields=["filename"]
)
index.fit(documents)


chunks = chunk_documents(documents, size=2000, step=1000)
search_results = index.search(
    question)
first_file_name =search_results[0].get('filename')
print ("What's the filename of the first result?")
print("The first file name result is of lessons is {first}".format(first=first_file_name)) 

load_dotenv(Path("/workspaces/01-agentic-rag/.venv/.env"))
##print(os.getenv("OPENAI_API_KEY"))

#load_dotenv()
True
openai_client = OpenAI(


     api_key=os.getenv("OPENAI_API_KEY"),
      base_url="https://api.openai.com/v1",
)

assistant = RAGBase (index,openai_client)
respone_assistance=[]
respone_assistance =assistant.rag('How does the agentic loop keep calling the model until it stops?')
print("How many input (prompt) tokens did we send to the model for this request?")
print("response is " \
"{first}".format(first=  respone_assistance[0]))


print ("How many chunks do you get? ")
print("response is " \
"{first}". format(first=  len(chunks)))


index_chunk = Index(
    text_fields=["content"],
    keyword_fields=["filename"]
)
index_chunk.fit(chunks)

assistant = RAGBase (index_chunk,openai_client)
respone_assistance_chunk=[]
respone_assistance_chunk =assistant.rag('How does the agentic loop keep calling the model until it stops?')
print("How many input (prompt) tokens did we send to the model for this request for chunk?")
print("response is " \
"{first}".format(first=  respone_assistance_chunk[0]))
print("Compare the input tokens with Q3. How many fewer input tokens does the chunked version send?")
rounded_number = int(respone_assistance[0]/respone_assistance_chunk[0])
print("response is " \
"{first}".format(first=  rounded_number) + " * fewer")

it = 0

def search_chunk(query: str) -> dict[str, str]:
    """
    Search for entries matching the given query.
    """
    
    
    return index_chunk.search(
      
        query,
        num_results=5,
       # boost_dict = {'content': 3.0, 'filename': 0.5},
        
    )


agent_tools = Tools()
agent_tools.add_tool(search_chunk)
agent_tools.get_tools()
chat_interface = IPythonChatInterface()
callback = DisplayingRunnerCallback(chat_interface)

runner = OpenAIResponsesRunner(
    
    tools=agent_tools,
    developer_prompt=instructions,
    chat_interface=chat_interface,
    llm_client=OpenAIClient(model='gpt-5.4-mini'),
    
)
result = runner.loop(
   
    prompt='How does the agentic loop work, and how is it different from plain RAG?',
    callback=callback,
)
#print (result)
respo= []
def search_call ():
   for response in result.all_messages :
    if getattr(response, "type", None)=="function_call" and getattr(response, "name", None)=="search_chunk"  :
    # print ("id: ")
    # print  (getattr(response, "id", None))

     respo.append(response)
   return len(respo)

lenth=search_call()
print ("How many times did the agent call ?")
print("response is " \
"{first}".format(first= lenth))



