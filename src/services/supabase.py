from supabase import create_client, Client
import httpx
import os
from dotenv import load_dotenv
from datetime import datetime
from supabase.lib.client_options import SyncClientOptions

from pathlib import Path
from uuid import uuid4
import mimetypes

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
        self.table_suppliers_plating = self.supabase.table('suppliers_plating')

        self.path_images = "productsImages"

    # Table Products
    def load_products(self):
        return self.table_products.select("*").execute().data

    def insert_product(self, content):
        return self.table_products.insert(content).execute()

    def update_product(self, id, data):
       return self.table_products.update(data).eq("id", id).execute()

    def delete_product(self, id):
        return (
            self.table_products
            .delete()
            .eq("id", id)
            .execute()
        )
    
    # Table Suppliers Plating
    def load_suppliers_plating(self):
        return self.table_suppliers_plating.select("*").execute().data

    def insert_suppliers_plating(self, content):
        return self.table_suppliers_plating.insert(content).execute()

    def update_suppliers_plating(self, id_supplier, data):
       return self.table_suppliers_plating.update(data).eq("id_supplier", id_supplier).execute()

    def delete_suppliers_plating(self, id_supplier):
        return (
            self.table_suppliers_plating
            .delete()
            .eq("id_supplier", id_supplier)
            .execute()
        )
    
    def upload_product_image(self, id_supplier, data):
       return self.table_suppliers_plating.update(data).eq("id_supplier", id_supplier).execute()
    
    def get_image_url(self, path):
        return self.supabase.storage.from_("images").get_public_url(path)
    
    def upload_image(self, image_file, image_name, content_type="application/octet-stream"):    
        storage_path = f"{self.path_images}/{image_name}"

        self.supabase.storage.from_("images").upload(
            path=storage_path,
            file=image_file,
            file_options={
                "content-type": content_type,
                "cache-control": "86400",
                "upsert": "false",
            },
        )

        return storage_path
    
    def upload_image_dev(self, path_image):
        file_path = Path(path_image)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {local_file_path}")
        
        extension = file_path.suffix.lower()
        unique_name = f"{uuid4()}{extension}"

        content_type, _ = mimetypes.guess_type(file_path.name)
        content_type = content_type or "application/octet-stream"

        with file_path.open("rb") as image_file:
            storage_path = self.upload_image(image_file, unique_name, content_type)
        
        return storage_path

    # def update_fallback_customer(self, phone_number, bool):
    #     date_now = None if bool else datetime.now().strftime("%Y-%m-%d")

    #     self.upsert({
    #         "phone_number": phone_number,
    #         "bot_active": bool,
    #         "date_bot_disabled": date_now
    #     }, 'customers')

    # def search_fallback_customer(self, phone_number):
    #     customers_fall_back = self.table_customers.select('*').eq('phone_number', phone_number).execute().data[0]

    #     # Caso o FallBack tenha passado de 2 dias
    #     if customers_fall_back['bot_active'] == False and customers_fall_back['date_bot_disabled'] != datetime.now().strftime("%Y-%m-%d"):
    #         self.update_fallback_customer(phone_number, True)
    #         customers_fall_back['bot_active'] = True

    #     return customers_fall_back['bot_active']
    
    # def search_block_bot(self, phone_number):
    #     return self.table_customers.select('*').eq('phone_number', phone_number).execute().data
    
    