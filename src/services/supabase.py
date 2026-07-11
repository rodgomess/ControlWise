from supabase import create_client, Client
import httpx
import os
from dotenv import load_dotenv
from datetime import datetime
from supabase.lib.client_options import SyncClientOptions

class SupabaseClient():
    def __init__(self):
        load_dotenv()
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_KEY = os.getenv('SUPABASE_KEY')

        httpx_client = httpx.Client(
            timeout=10.0,
            verify=True,
        )

        self.supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
            options=SyncClientOptions(
                httpx_client=httpx_client,
            ),
        )
        
        self.table_products = self.supabase.table('products')
                
    def update_product2(self, data):
       self.table_products.upsert(data).execute()

    def update_product(self, id, data):
       response = self.table_products.update(data).eq("id", id).execute()
    
    def load_products(self):
        return self.table_products.select("*").execute().data
    
    def insert_product(self, content):
        self.upsert(content, 'products')
    
    def update_fallback_customer(self, phone_number, bool):
        date_now = None if bool else datetime.now().strftime("%Y-%m-%d")

        self.upsert({
            "phone_number": phone_number,
            "bot_active": bool,
            "date_bot_disabled": date_now
        }, 'customers')

    def search_fallback_customer(self, phone_number):
        customers_fall_back = self.table_customers.select('*').eq('phone_number', phone_number).execute().data[0]

        # Caso o FallBack tenha passado de 2 dias
        if customers_fall_back['bot_active'] == False and customers_fall_back['date_bot_disabled'] != datetime.now().strftime("%Y-%m-%d"):
            self.update_fallback_customer(phone_number, True)
            customers_fall_back['bot_active'] = True

        return customers_fall_back['bot_active']
    
    def search_block_bot(self, phone_number):
        return self.table_customers.select('*').eq('phone_number', phone_number).execute().data
    
    