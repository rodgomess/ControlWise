from supabase import create_client
import httpx
import os
from dotenv import load_dotenv
from supabase.lib.client_options import SyncClientOptions
from pathlib import Path

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
        self.table_suppliers_plating_prices = self.supabase.table('suppliers_plating_prices')

        self.bucket = self.supabase.storage.from_("images")
        self.container_images = "productsImages"

    # Table Products
    def load_products(self):
        return self.table_products.select("*").execute().data

    def insert_product(self, content):
        return self.table_products.insert(content).execute()

    def update_product(self, id, data):
       return self.table_products.update(data).eq("id", id).execute()
    
    def update_list_products(self, data):
        if not data:
            return None

        return (
            self.table_products
            .upsert(
                data,
                on_conflict="id",
                default_to_null=False,
            )
            .execute()
        )
    
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

    # Table Suppliers Plating Pricing
    def load_suppliers_plating_prices(self):
        return self.table_suppliers_plating_prices.select("*").execute().data

    def insert_suppliers_plating_prices(self, content):
        return self.table_suppliers_plating_prices.insert(content).execute()

    def update_suppliers_plating_prices(self, id_supplier, plating_metal, plating_classification, data):
       return  (
            self.table_suppliers_plating_prices
            .update(data)
            .eq("id_supplier", id_supplier)
            .eq("plating_metal", plating_metal)
            .eq("plating_classification", plating_classification)
            .execute()
        )

    def delete_suppliers_plating_prices(self, id_supplier, plating_metal, plating_classification):
        return (
            self.table_suppliers_plating_prices
            .delete()
            .eq("id_supplier", id_supplier)
            .eq("plating_metal", plating_metal)
            .eq("plating_classification", plating_classification)
            .execute()
        )
    
    # Images
    def get_product_images_url(self, product_id):
        directory = f"{self.container_images}/{product_id}"

        files = self.bucket.list(directory)

        images = {
            "original_url_image": None,
            "thumbnail_url_image": None,
        }

        for file in files:
            file_name = file.get("name")

            if not file_name:
                continue

            file_path = f"{directory}/{file_name}"
            image_url = self.bucket.get_public_url(file_path)

            # Remove a extensão e compara somente o nome
            file_stem = Path(file_name).stem.lower()

            if file_stem == "original":
                images["original_url_image"] = image_url

            elif file_stem == "thumbnail":
                images["thumbnail_url_image"] = image_url

        return images
    
    def upload_product_image(self, image_file, image_name,  product_id, content_type="application/octet-stream"):    
        storage_path = f"{self.container_images}/{product_id}/{image_name}"

        self.supabase.storage.from_("images").upload(
            path=storage_path,
            file=image_file,
            file_options={
                "content-type": content_type,
                "cache-control": "86400",
                "upsert": "true",
            },
        )
        return storage_path

    def delete_product_images(self, product_id: str):
        directory = f"{self.container_images}/{product_id}"
        
        files = self.bucket.list(
            directory,
            {
                "limit": 100,
                "offset": 0,
            },
        )

        if not files:
            return []
        
        file_paths = [
            f"{directory}/{file['name']}"
            for file in files
        ]
        
        response = self.bucket.remove(file_paths)

        return response
    