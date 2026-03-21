import psycopg
import pandas as pd
import os



DATABASE_URL =  os.getenv("DATABASE_URL")

def sql_execute(sql, params=None):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        
def sql_execute_many(sql, params_seq):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, params_seq)
        conn.commit()
        conn.close()
        

def sql_retrieve(sql, params=None):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql,params)
            if cur.description is not None:
                return cur.fetchone()
            else:
                return None



def convert_to_df():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            return pd.read_sql("SELECT * FROM call_sessions", conn)
            

    
def new_call_sql(streamsid, caller_number):
    sql = """
    INSERT INTO call_sessions (streamsid, caller_number) VALUES(%s,%s)
    """
    sql_execute(sql, (streamsid,caller_number))
    
    
def update_location(streamsid, latitude, longitude, location_text):
    sql = """
    UPDATE call_sessions
    SET latitude = %s,
        longitude = %s,
        location_text = %s,
        updated_at = NOW()
    WHERE streamsid = %s
        
    
    """
    sql_execute(sql,(latitude, longitude, location_text, streamsid))
    
    
def get_emergency_description(streamsid):
    query = """
    SELECT emergency_description FROM call_sessions
    WHERE streamsid = %s
    """
    result = sql_retrieve(query,(streamsid,))
    existing_emergency_description = result[0]
    print(f"existing_emergency_description: {existing_emergency_description}")
    return existing_emergency_description
    
    
def update_emergency_description(streamsid, emergency_description):
    existing_emergency_description = get_emergency_description(streamsid)
    
    if existing_emergency_description is not None:
        emergency_description = existing_emergency_description + "\n\n" + emergency_description
    
    sql = """
    UPDATE call_sessions
    SET emergency_description = %s,
        updated_at = NOW()
    WHERE streamsid = %s"""
    
    sql_execute(sql,(emergency_description, streamsid))

    return existing_emergency_description
    

## __________________________________________________ NEEDS TO GET MODIFIED

def update_esi(streamsid, esi, justification):
    
    sql = """
    UPDATE call_sessions
    SET esi = %s,
        esi_justification = %s,
        updated_at = NOW()
    WHERE streamsid = %s"""
    
    sql_execute(sql,(esi, justification, streamsid))
    

    
def update_assigned_status(task_list: list):

    sql = f"""
    UPDATE call_sessions
    SET assigned = %s
    WHERE streamsid = %s;
    """
    
    sql_execute_many(sql, task_list)


def update_esi_status(task_list: list):

    sql = f"""
    UPDATE call_sessions
    SET esi = %s
    WHERE streamsid = %s;
    """
    
    sql_execute_many(sql, task_list)
    