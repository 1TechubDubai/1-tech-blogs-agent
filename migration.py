import firebase_admin
from firebase_admin import credentials, firestore

# 1. Connect to the OLD database (Source)
old_cred = credentials.Certificate('old_service_account.json')
old_app = firebase_admin.initialize_app(old_cred, name='old_app')
old_db = firestore.client(app=old_app)

# 2. Connect to the NEW database (Destination)
new_cred = credentials.Certificate('service_account.json')
new_app = firebase_admin.initialize_app(new_cred, name='new_app')
new_db = firestore.client(app=new_app)

# 3. Define the collections you want to copy (e.g., 'blogs', 'users')
collections_to_copy = ['blog_posts', 'messages', 'service_listings', 'system_settings', 'users']

def migrate_data():
    print("Starting migration...")
    
    for collection_name in collections_to_copy:
        print(f"Copying collection: {collection_name}...")
        docs = old_db.collection(collection_name).stream()
        
        count = 0
        for doc in docs:
            # Read from old, write to new with the EXACT same document ID
            new_db.collection(collection_name).document(doc.id).set(doc.to_dict())
            count += 1
            
        print(f"Copied {count} documents in '{collection_name}'.")

    print("Migration complete! You can now use your new project.")

if __name__ == "__main__":
    migrate_data()