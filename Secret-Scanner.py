import os
import re
import subprocess
import time
from tqdm import tqdm
from colorama import init, Fore

# Initialize colorama
init(autoreset=True)

APKTOOL_PATH = 'apktool_2.7.0.jar'

# Additional keywords to find sensitive hardcoded values
SENSITIVE_KEYWORDS = [' token ', 'TOKEN', 'TOKENS', 'tokens', ' key ',
                      'password', 'secret', 'SECRET', 'confidential', '_key', '_token', 'api_key']

# Decorator to print tool name with ASCII art

def print_tool_name(func):
    def wrapper(*args, **kwargs):
        print(r'''
  /$$$$$$                                            /$$            /$$$$$$                    
 /$$__  $$                                          | $$           /$$__  $$                         
| $$  \__/  /$$$$$$   /$$$$$$$  /$$$$$$   /$$$$$$  /$$$$$$        | $$  \__/  /$$$$$$$  /$$$$$$  / $$$$$$ \ / $$$$$$ \  /$$$$$$   /$$$$$$
|  $$$$$$  /$$__  $$ /$$_____/ /$$__  $$ /$$__  $$|_  $$_/        |  $$$$$$  /$$_____/ |____  $$| $$    $$ | $$    $$ |/$$__  $$ /$$__  $$
 \____  $$| $$$$$$$$| $$      | $$  \__/| $$$$$$$$  | $$           \____  $$| $$        /$$$$$$$| $$    $$ | $$    $$ | $$$$$$$$| $$  \__/
 /$$  \ $$| $$_____/| $$      | $$      | $$_____/  | $$ /$$       /$$  \ $$| $$       /$$__  $$| $$    $$ | $$    $$ | $$_____/| $$
|  $$$$$$/|  $$$$$$$|  $$$$$$$| $$      |  $$$$$$$  |  $$$$/      |  $$$$$$/|  $$$$$$$ | $$$$$$ | $$    $$ | $$    $$ |  $$$$$$$| $$
 \______/  \_______/ \_______/|__/       \_______/   \___/         \______/  \_______/ \________/\___/ \___/\___/ \___/\_______/|__/
                                                                                                                                                        
        github.com/ajayhackz
        ''')
        print("Welcome to the Secret Scanner!")


        return func(*args, **kwargs)

    return wrapper


# Decompiles the specified APK file


def decompile_apk(apk_path):
    # Remove double quotes from the APK path
    apk_path = apk_path.strip('"')

    # Extract the APK file name without extension
    apk_name = os.path.splitext(os.path.basename(apk_path))[0]

    # Replace spaces with underscores in the APK name
    apk_name = apk_name.replace(' ', '_')

    # Create a new directory in the current working directory
    decompiled_path = os.path.join(os.getcwd(), apk_name + '_decompiled')

    print(
        f"Decompiling APK: {apk_path} It may take some time, please wait...\n ")

    # Start the decompilation process
    process = subprocess.Popen(['java', '-jar', APKTOOL_PATH, 'd', apk_path, '-o', decompiled_path],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    pbar = None

    while True:
        output = process.stdout.readline().strip()
        if output:
            match = re.search(r'(\d+)%', output)
            if match:
                progress = int(match.group(1))
                if not pbar:
                    pbar = tqdm(total=100, desc="Decompiling",
                                unit="%", leave=True)
                pbar.n = progress
                pbar.refresh()
        else:
            break

    process.wait()
    if pbar:
        pbar.close()

    if process.returncode == 0:
        print("APK decompiled successfully!")
        print(f"Decompiled files saved in: {decompiled_path}")
    else:
        print("Failed to decompile APK.")
        print(process.stderr.read())

    return decompiled_path


# Checks a file for matching sensitive keywords
def check_file_for_sensitive_keywords(file_path):
    matches = []

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()
                for keyword in SENSITIVE_KEYWORDS:
                    if keyword in line.lower():
                        matches.append((file_path, line_number, line))
                        break
    except UnicodeDecodeError:
        print(f"Failed to decode file: {file_path}")

    return matches

# Checks the APK for matching sensitive keywords in specified file(s) or all files


def check_apk_for_sensitive_keywords(apk_path, check_all_files=False):
    decompiled_path = decompile_apk(apk_path)

    print("Searching for sensitive strings in all files...\n")

    matches = []
    total_files = 0

    if check_all_files:
        for root, _, files in os.walk(decompiled_path):
            for file in files:
                if file.endswith(".smali"):  # Only process *.smali files
                    total_files += 1

        with tqdm(total=total_files, desc="Progress", unit="file") as pbar:
            for root, _, files in os.walk(decompiled_path):
                for file in files:
                    if file.endswith(".smali"):  # Only process *.smali files
                        file_path = os.path.join(root, file)
                        file_matches = check_file_for_sensitive_keywords(
                            file_path)
                        if file_matches:
                            matches.extend(file_matches)
                        pbar.update(1)
                        # Optional delay for smoother progress display
                        time.sleep(0.01)
    else:
        strings_xml_path = os.path.join(
            decompiled_path, 'res', 'values', 'strings.xml')
        manifest_xml_path = os.path.join(
            decompiled_path, 'AndroidManifest.xml')

        total_files = 2
        pbar = tqdm(total=total_files, desc="Progress", unit="file")

        strings_matches = check_file_for_sensitive_keywords(strings_xml_path)
        manifest_matches = check_file_for_sensitive_keywords(manifest_xml_path)

        matches.extend(strings_matches)
        matches.extend(manifest_matches)
        pbar.update(total_files)

    return matches

# Main function


@print_tool_name
def main():
    apk_path = input("Enter the path to the APK file: ")

    if not os.path.isfile(apk_path):
        print(Fore.RED + "The specified APK file does not exist.")
        return

    while True:
        try:
            file_check_option = int(input(
                "Select file check option \n1. Basic Scan(Fast - Check for only important)\n2. Advance Scan(Slow - Check for All files): "))
            if file_check_option in [1, 2]:
                break
            else:
                print(Fore.RED + "Invalid option selected. Please try again.")
        except ValueError:
            print(Fore.RED + "Please enter a valid integer.")

    if file_check_option == 1:
        sensitive_matches = check_apk_for_sensitive_keywords(apk_path)
    else:
        sensitive_matches = check_apk_for_sensitive_keywords(apk_path, check_all_files=True)

    if not sensitive_matches:
        print(Fore.RED + "No sensitive strings found.")
    else:
        print(Fore.RED + "\nSensitive strings found:\n")
        for match in sensitive_matches:
            print(Fore.GREEN + f"File: {match[0]}")
            print(Fore.GREEN + f"Line Number: {match[1]}")
            print(Fore.GREEN + f"Line: {match[2]}\n")

if __name__ == '__main__':
    main()
