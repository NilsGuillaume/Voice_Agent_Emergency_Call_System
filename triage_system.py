

from openai import OpenAI
from pydantic import BaseModel
import os
#from db import update_needs

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

from db import update_esi

class ESI_1_Quali(BaseModel):
    esi: bool
    justification: str


#__________________________________REMOVE
"""
def analyse_emergency_description(streamsid, emergency_description):

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "system",
                "content": "Document the medical needs based on the emergency description. What interventions are recommended in such a situation?"
            },
            {
                "role": "user",
                "content": emergency_description
            }
        ],
        
        temperature=0,
    )
    needs = response.output_text
    print(response.output_text)
    
    update_needs(streamsid, needs)
"""
#________________________________#

with open("Triage_System_Prompts/esi_life_saving_interv_prompt.txt","r") as f:
    esi_life_saving_interv_prompt = f.read()
 
  
with open("Triage_System_Prompts/esi_high_risk_prompt.txt","r") as f:
    esi_high_risk_prompt = f.read()
 
  
    
    
    
def esi_life_saving_interv(emergency_description):


    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": esi_life_saving_interv_prompt},
            {"role": "user", "content": emergency_description},
        ],
        response_format=ESI_1_Quali,
        temperature=0
    )

    event = completion.choices[0].message.parsed
  
    return event



def esi_high_risk(emergency_description):
    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": esi_high_risk_prompt},
            {"role": "user", "content": emergency_description},
        ],
        response_format=ESI_1_Quali,
        temperature=0
    )

    event = completion.choices[0].message.parsed
  
    return event

def esi_how_many_ressources(emergency_description):
    pass

def vital_signs(emergency_descriptions):
    pass
    





def esi_determine(emergency_description):
    
    esi_pred = None

    esi_1_status = esi_life_saving_interv(emergency_description)
    if esi_1_status.esi:
        esi_pred = 1
        esi_justification =  f"Reason for ESI 1: \n {esi_1_status.justification}"
        
    else:
        esi_2_status = esi_high_risk(emergency_description)
        if esi_2_status.esi:
            esi_pred = 2
            esi_justification = (
                f"Reason for ESI 2: \n {esi_2_status.justification}" +
                f"\n\n Reason against ESI 1: \n {esi_1_status.justification}")
        
        else:
            esi_pred = 3
            esi_justification = (
                f"Reason against ESI 2: \n {esi_2_status.justification}" +
                f"\n\n Reason against ESI 1: \n {esi_1_status.justification}")
        
        
            
    return esi_pred, esi_justification





def main_call_update_esi(streamsid, emergency_description):
    esi, esi_justification = esi_determine(emergency_description)
    update_esi(streamsid, esi, esi_justification)






