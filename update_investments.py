import csv

input_file = "investments_export.csv"
output_file = "investments_export.csv.updated"

# New facts to add
# ID,Startup,Investor,Round,Amount USD,Date,Status
new_deals = [
    # Epic Games
    {"ID": "147", "Startup": "Epic Games", "Investor": "Sony & KIRKBI", "Round": "Corporate Round", "Amount USD": "2000000000", "Date": "2022-04-11", "Status": "Concluded"},
    {"ID": "148", "Startup": "Epic Games", "Investor": "The Walt Disney Company", "Round": "Corporate Round", "Amount USD": "1500000000", "Date": "2024-02-07", "Status": "Concluded"},
    # OpenAI
    {"ID": "149", "Startup": "OpenAI", "Investor": "Microsoft", "Round": "Corporate Round", "Amount USD": "1000000000", "Date": "2019-07-22", "Status": "Concluded"},
    {"ID": "150", "Startup": "OpenAI", "Investor": "Microsoft", "Round": "Corporate Round", "Amount USD": "10000000000", "Date": "2023-01-23", "Status": "Concluded"},
    # Anthropic
    {"ID": "151", "Startup": "Anthropic", "Investor": "Amazon", "Round": "Corporate Round", "Amount USD": "4000000000", "Date": "2023-09-25", "Status": "Concluded"},
    {"ID": "152", "Startup": "Anthropic", "Investor": "Google", "Round": "Corporate Round", "Amount USD": "2000000000", "Date": "2023-10-27", "Status": "Concluded"},
]

keep_ids = {"3", "4"} # Stripe Series I, GitHub M&A

with open(input_file, "r") as f_in, open(output_file, "w", newline="") as f_out:
    reader = csv.DictReader(f_in)
    fieldnames = reader.fieldnames
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in reader:
        if row["ID"] in keep_ids:
            writer.writerow(row)
            
    for deal in new_deals:
        writer.writerow(deal)

print("Writing done.")
