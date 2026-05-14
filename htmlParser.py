import pyodbc
import json
from bs4 import BeautifulSoup
#databsae connection
try:
    conn=pyodbc.connect(
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=10.11.12.14,1435;"
        "Database=MBL_ITG;"
        "UID=devuser;"
        "PWD=wh!zzk!dz786?"
    )
    print("✅Connected to database Successfully")
except Exception as e:
    print(f"❌Error connecting to database: {e}")
    exit(1)
    

cursor=conn.cursor()

#query to retrieve documents from database
cursor.execute("""select * from compliance_Rule where COMPLIANCECATEGORY in (select COMPLIANCECATEGORY_ID  from compliancecategory where COMPLIANCECATEGORY_KEY like 'PCC01%' )""")

def clean_description(html_desc):
    #if the description is empty
    if not html_desc:
        return None
    #parsing the html description into text
    text=BeautifulSoup(html_desc,"html.parser").get_text(separator="\n",strip=True)
    text=text.strip()
    
    #ignoring dummay data
    if not text or "lorem ipsum" in text.lower():
        return None
    
    #checking if the length of the description is less than 10 letters
    if len(text.strip())<10:
        return None
    
    return text

#creating Output json for the context
result_json=[]
#fetching data from database
for row in cursor.fetchall():
    cleaned_desc=clean_description(row.DESCRIPTION)
    
    #creating each json object
    if cleaned_desc:
        result_json.append({
            "ComplianceRuleID":row.COMPLIANCERULE_ID,
            "Title":row.TITLE,
            "Description":cleaned_desc,
            "CreatedOn":row.CREATEDON.isoformat() if row.CREATEDON else None
        })

#save the results to a json file
with open("compliance_rules_clean.json", "w", encoding="utf-8") as f:
    json.dump(result_json, f, indent=4, ensure_ascii=False)

#printing the length of the json
print(f"✅{len(result_json)} compliance rules processed and saved to compliance_rules.json")