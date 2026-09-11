from bs4 import BeautifulSoup
import pandas as pd
import argparse
import os
import requests
import tarfile

def download_miniml_file(GSE):
    stub = GSE[:-3] + 'nnn'  # Replace the last three characters of the accession with "nnn"
    url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{stub}/{GSE}/miniml/{GSE}_family.xml.tgz"
    output_file = f"{GSE}_family.xml.tgz"
    output_xml_file = f"{GSE}_family.xml"

    print(f"Downloading MINiML file for accession {GSE}...")

    try:
        # Send an HTTP GET request to download the file
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Save the downloaded file
        with open(output_file, 'wb') as file:
            file.write(response.content)

        print("Downloaded MINiML file successfully.")

        # Extract the downloaded archive
        with tarfile.open(output_file, 'r:gz') as tar:
            tar.extractall()

        print(f"Extracted MINiML file: {output_xml_file}")

    except requests.exceptions.RequestException as e:
        print(f"Failed to download MINiML file for accession {GSE}: {e}")
    except tarfile.TarError as e:
        print(f"Failed to extract the downloaded archive: {e}")
    finally:
        # Clean up: Remove the downloaded archive if it exists
        if os.path.exists(output_file):
            os.remove(output_file)

def extract_samples(GSE):
    with open(f'{GSE}_family.xml', 'r', encoding='utf-8') as file:
    	xml_data = file.read()

    # Prefer XML parser when available, but fall back to html.parser if lxml is absent.
    try:
        soup = BeautifulSoup(xml_data, 'xml')
        if not soup.find('Sample'):
            raise ValueError("No Sample tags found via XML parser")
    except Exception:
        soup = BeautifulSoup(xml_data, 'html.parser')
    samples = soup.find_all('Sample')
    return samples

def filter_organism(samples,organism):
    #extract only human samples
    org_samples = []
    for sample in samples:
        organism_tag = sample.find('Organism')
        if organism_tag.text == organism:
            org_samples.append(sample)
    return org_samples

def filter_platform(samples, platform_id):
    platform_samples = []
    #print(platform_id)
    for sample in samples:
        platform_ref = sample.find('Platform-Ref')
        if platform_ref and 'ref' in platform_ref.attrs and platform_ref['ref'] == platform_id:
            platform_samples.append(sample)
    return platform_samples

def filter_platform_organism(samples, platform_id, organism_name):
    filtered_samples = []
    for sample in samples:
        platform_ref = sample.find('Platform-Ref')
        organism_tag = sample.find('Organism') 
        if (
            platform_ref['ref']  == platform_id and
            organism_tag.text == organism_name
        ):
            filtered_samples.append(sample)
    return filtered_samples

def extract_metadata(matching_samples):
    sample_dfs = []

    # Iterate through matching_samples
    for sample in matching_samples:
        sample_id = sample.get('iid', None)
        title_tag = sample.find("Title")
        title = title_tag.text if title_tag else ""
        organism_tag = sample.find('Organism')
        org = organism_tag.text if organism_tag else ""
        biosample_tag = sample.find('Relation', target=True, type='BioSample')
        biosample_url = biosample_tag['target'] if biosample_tag and 'target' in biosample_tag.attrs else ""
        biosample_id = biosample_url.split("/")[-1] if biosample_url else ""
        chars = sample.find_all('Characteristics')
        instrument_model_tag = sample.find('Instrument-Model')
        predefined_tag = instrument_model_tag.find('Predefined') if instrument_model_tag else None
        instrument_model = predefined_tag.text if predefined_tag else ""
        extract_protocol_tag = sample.find('Extract-Protocol')
        extract_protocol = extract_protocol_tag.text.strip() if extract_protocol_tag and extract_protocol_tag.text else ""
        library_strategy_tag = sample.find('Library-Strategy')
        library_strategy = library_strategy_tag.text if library_strategy_tag else ""
        
        # Create a dictionary to store the characteristics for this sample
        sample_dict = {'Sample_ID': sample_id, 'Title': title, 'Organism': org, 'BioSample_ID': biosample_id, 'Instrument model': instrument_model, 'Extraction protocol': extract_protocol, 'Library strategy': library_strategy}

        # Iterate through characteristics for each sample and add them to the dictionary
        for characteristic in chars:
            tag = characteristic.get('tag', None)
            value = characteristic.text.strip()
            sample_dict[tag] = value

        # Append the dictionary as a row to a temporary DataFrame
        sample_df = pd.DataFrame([sample_dict])
        sample_dfs.append(sample_df)
    sample_df = pd.concat(sample_dfs, ignore_index=True)
    return sample_df

def main(args):
    #organism = args.organism
    GSE=args.GSE
    download_miniml_file(GSE)
    samples=extract_samples(GSE)
    matching_samples=[]
    if args.organism and not args.platform:
        organism = args.organism
        matching_samples.extend(filter_organism(samples,organism))
    if args.platform and not args.organism:
        platform_id=args.platform
        matching_samples.extend(filter_platform(samples,platform_id))
    if args.platform and args.organism:
        platform_id=args.platform
        organism = args.organism
        matching_samples.extend(filter_platform_organism(samples, platform_id, organism))
                                
    if not matching_samples:
        matching_samples=samples
        
    sample_df=extract_metadata(matching_samples)
    sample_df.to_csv(path_or_buf=GSE + '.tsv', sep='\t', index=False)
    print("Wrote samples to " + GSE + ".tsv")

if __name__ == '__main__':
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Download and extract metadata from an XML file for a given GSE accession.")

    # Add an argument for the GSE accession
    parser.add_argument("GSE", type=str, help="The GSE accession to download")
    parser.add_argument("--organism", type=str, help="Filter on given organism name")
    parser.add_argument("--platform", type=str, help="Filter on given platform ID")

    # Parse the command-line arguments
    args = parser.parse_args()
    main(args)
