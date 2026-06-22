
from minsearch import Index
INSTRUCTIONS = '''
Your task is to answer questions from the course participants
based on the provided context.

Use the context to find relevant information and provide accurate
answers. If the answer is not found in the context,
respond with "I don't know."
'''


PROMPT_TEMPLATE = '''
QUESTION: {question}
CONTEXT:
{context}
'''.strip()


class RAGBase:

    def __init__(
        self,
        index,
        llm_client,
        instructions=INSTRUCTIONS,
        prompt_template=PROMPT_TEMPLATE,
        model='gpt-5.4-mini'
    ):
        self.index =  index
        self.llm_client = llm_client
        self.instructions = instructions
        self.prompt_template = prompt_template
        self.model = model


    def search(self, query, num_results=5):
        
        boost_dict = {'content': 3.0, 'filename': 0.5}
        


        return self.index.search(
            query,
            num_results=num_results,
            boost_dict=boost_dict,
           
           
        )

    def build_context(self, search_results):
        lines = []

        for doc in search_results:
          
            lines.append(doc['filename'])
            lines.append(doc['content'])
          

        return ''.join(lines).strip()


    def build_prompt(self, query, search_results):
        context = self.build_context(search_results)
        
        return self.prompt_template.format(
            question=query, context=context
        )
   

    def llm(self, prompt):
        input_messages = [
            {'role': 'developer', 'content': self.instructions},
            {'role': 'user', 'content': prompt}
         ]
        
        response = self.llm_client.responses.create (
            model=self.model,
            input=input_messages
            
        )
       
        
        return response
    
    
    def rag(self, query):
        search_results = self.search(query)
        prompt = self.build_prompt(query, search_results)
        answer = self.llm(prompt).output_text
        usage = self.llm(prompt).usage.input_tokens
        answer_from_rag=[]
        answer_from_rag.append(usage)
        answer_from_rag.append(answer)
      
        return answer_from_rag