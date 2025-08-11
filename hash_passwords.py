import streamlit_authenticator as stauth

# Generate hashed passwords for all companies
# Using company name + "123" as password pattern
companies = ['WBSC', 'WLAC', 'WWG', 'WCA', 'WUSA', 'WMCF', 'DAKOTA']
passwords = [f"{company}123" for company in companies]

hashed_passwords = stauth.Hasher(passwords).generate()

print("Hashed passwords for all companies:")
print("="*50)
for i, company in enumerate(companies):
    username = company.lower()
    password = passwords[i]
    hashed_pw = hashed_passwords[i]
    print(f"Company: {company}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Hashed: {hashed_pw}")
    print("-" * 30)
