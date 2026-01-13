import os

source_file = 'avis/consolidated_reviews_FINAL.csv'
dest_file = 'avis/consolidated_reviews_sample.csv'
max_size = 100 * 1024 * 1024  # 100 MB

current_size = 0

try:
    with open(source_file, 'r', encoding='utf-8', errors='replace') as f_in, \
         open(dest_file, 'w', encoding='utf-8', newline='') as f_out:
        
        header = f_in.readline()
        f_out.write(header)
        current_size += len(header.encode('utf-8'))
        
        for line in f_in:
            line_size = len(line.encode('utf-8'))
            if current_size + line_size > max_size:
                break
            f_out.write(line)
            current_size += line_size
            
    print(f"Sample created at {dest_file}, size: {current_size / (1024*1024):.2f} MB")

except FileNotFoundError:
    print(f"Error: {source_file} not found.")
except Exception as e:
    print(f"An error occurred: {e}")
