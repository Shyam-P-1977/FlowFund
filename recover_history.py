import os
import json
import shutil

history_dir = os.path.expandvars(r'%APPDATA%\Code\User\History')
recovery_dir = r'c:\Users\saksh\Desktop\Odoo\frontend_recovered'
os.makedirs(recovery_dir, exist_ok=True)

# We want to recover 14 files we know were in frontend based on list_dir output from before:
target_files = [
    'admin.html', 'admin_dashboard.html', 'dashboard.html', 
    'employee_dashboard.html', 'employee_register.html', 'expense.html', 
    'index.html', 'login.html', 'manager_dashboard.html', 
    'manager_register.html', 'signup.html', 'api.js', 'ui.js', 'styles.css'
]

if not os.path.exists(history_dir):
    print("No history found")
    exit()

recovered_count = 0

for file_hash in os.listdir(history_dir):
    hash_dir = os.path.join(history_dir, file_hash)
    entries_file = os.path.join(hash_dir, 'entries.json')
    
    if os.path.isdir(hash_dir) and os.path.exists(entries_file):
        try:
            with open(entries_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            original_path = data.get('resource', '').replace('file:///', '').replace('%3A', ':')
            parts = original_path.replace('\\', '/').split('/')
            filename = parts[-1]
            
            # Check if this file is one of our targets AND belonged to the Odoo/frontend path
            if filename in target_files and 'Odoo' in original_path and 'frontend' in original_path:
                entries = data.get('entries', [])
                if entries:
                    # Get the most recent entry
                    latest_entry = entries[-1]
                    file_id = latest_entry.get('id')
                    backup_path = os.path.join(hash_dir, file_id)
                    
                    if os.path.exists(backup_path):
                        # Construct the relative path inside the recovery dir
                        # For css and js files, put them in their subdirectories
                        if filename.endswith('.css'):
                            dest_dir = os.path.join(recovery_dir, 'css')
                        elif filename.endswith('.js'):
                            dest_dir = os.path.join(recovery_dir, 'js')
                        else:
                            dest_dir = recovery_dir
                            
                        os.makedirs(dest_dir, exist_ok=True)
                        dest_path = os.path.join(dest_dir, filename)
                        
                        # Copy it over!
                        shutil.copy2(backup_path, dest_path)
                        print(f"Recovered {filename} to {dest_path}")
                        recovered_count += 1
        except Exception as e:
            pass

print(f"Total files recovered: {recovered_count}")
