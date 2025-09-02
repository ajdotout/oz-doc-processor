#!/usr/bin/env python3
"""
US Census Bureau API Test Script

This script tests the US Census Bureau API to fetch demographic and economic data
for market analysis sections like marketMetrics and demographics.

Required API Key: Get from https://api.census.gov/data/key_signup.html
"""

import os
import requests
import json
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Load environment variables
load_dotenv()

console = Console()

class CensusAPITester:
    def __init__(self):
        self.api_key = os.getenv('CENSUS_API_KEY')
        self.base_url = 'https://api.census.gov/data'
        self.test_county_fips = os.getenv('TEST_COUNTY_FIPS', '06085')  # Santa Clara County, CA
        self.test_state_fips = os.getenv('TEST_STATE_FIPS', '06')  # California
        
        if not self.api_key:
            console.print("[red]Error: CENSUS_API_KEY not found in environment variables[/red]")
            console.print("Please set your Census API key in the .env file")
            exit(1)
    
    def test_population_data(self):
        """Test fetching population data for a county"""
        console.print("\n[bold blue]Testing Population Data Fetch[/bold blue]")
        
        # ACS 5-Year Data for 2022
        url = f"{self.base_url}/2022/acs/acs5"
        params = {
            'get': 'NAME,B01003_001E',  # Total population
            'for': f'county:{self.test_county_fips}',
            'in': f'state:{self.test_state_fips}',
            'key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if len(data) > 1:
                headers = data[0]
                county_data = data[1]
                
                table = Table(title="Population Data")
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="green")
                
                for i, header in enumerate(headers):
                    table.add_row(header, str(county_data[i]))
                
                console.print(table)
                console.print(f"[green]✓ Successfully fetched population data[/green]")
                return data
            else:
                console.print("[red]✗ No data returned[/red]")
                return None
                
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗ Error fetching population data: {e}[/red]")
            return None
    
    def test_income_data(self):
        """Test fetching median household income data"""
        console.print("\n[bold blue]Testing Income Data Fetch[/bold blue]")
        
        url = f"{self.base_url}/2022/acs/acs5"
        params = {
            'get': 'NAME,B19013_001E',  # Median household income
            'for': f'county:{self.test_county_fips}',
            'in': f'state:{self.test_state_fips}',
            'key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if len(data) > 1:
                headers = data[0]
                county_data = data[1]
                
                table = Table(title="Income Data")
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="green")
                
                for i, header in enumerate(headers):
                    table.add_row(header, str(county_data[i]))
                
                console.print(table)
                console.print(f"[green]✓ Successfully fetched income data[/green]")
                return data
            else:
                console.print("[red]✗ No data returned[/red]")
                return None
                
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗ Error fetching income data: {e}[/red]")
            return None
    
    def test_age_distribution(self):
        """Test fetching age distribution data"""
        console.print("\n[bold blue]Testing Age Distribution Data Fetch[/bold blue]")
        
        # Age groups: 25-34, 35-44, 45-54, 55-64
        age_variables = [
            'B01001_010E',  # Male 25-29
            'B01001_011E',  # Male 30-34
            'B01001_012E',  # Male 35-39
            'B01001_013E',  # Male 40-44
            'B01001_014E',  # Male 45-49
            'B01001_015E',  # Male 50-54
            'B01001_016E',  # Male 55-59
            'B01001_017E',  # Male 60-64
            'B01001_034E',  # Female 25-29
            'B01001_035E',  # Female 30-34
            'B01001_036E',  # Female 35-39
            'B01001_037E',  # Female 40-44
            'B01001_038E',  # Female 45-49
            'B01001_039E',  # Female 50-54
            'B01001_040E',  # Female 55-59
            'B01001_041E',  # Female 60-64
        ]
        
        url = f"{self.base_url}/2022/acs/acs5"
        params = {
            'get': f'NAME,{",".join(age_variables)}',
            'for': f'county:{self.test_county_fips}',
            'in': f'state:{self.test_state_fips}',
            'key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if len(data) > 1:
                headers = data[0]
                county_data = data[1]
                
                # Calculate age groups
                age_groups = {
                    '25-34': int(county_data[1]) + int(county_data[2]) + int(county_data[9]) + int(county_data[10]),
                    '35-44': int(county_data[3]) + int(county_data[4]) + int(county_data[11]) + int(county_data[12]),
                    '45-54': int(county_data[5]) + int(county_data[6]) + int(county_data[13]) + int(county_data[14]),
                    '55-64': int(county_data[7]) + int(county_data[8]) + int(county_data[15]) + int(county_data[16])
                }
                
                table = Table(title="Age Distribution (25-64)")
                table.add_column("Age Group", style="cyan")
                table.add_column("Population", style="green")
                
                for age_group, population in age_groups.items():
                    table.add_row(age_group, f"{population:,}")
                
                console.print(table)
                console.print(f"[green]✓ Successfully fetched age distribution data[/green]")
                return data
            else:
                console.print("[red]✗ No data returned[/red]")
                return None
                
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗ Error fetching age distribution data: {e}[/red]")
            return None
    
    def test_education_data(self):
        """Test fetching educational attainment data"""
        console.print("\n[bold blue]Testing Education Data Fetch[/bold blue]")
        
        # Educational attainment variables
        education_variables = [
            'B15003_022E',  # Bachelor's degree
            'B15003_023E',  # Master's degree
            'B15003_024E',  # Professional degree
            'B15003_025E',  # Doctorate degree
        ]
        
        url = f"{self.base_url}/2022/acs/acs5"
        params = {
            'get': f'NAME,{",".join(education_variables)}',
            'for': f'county:{self.test_county_fips}',
            'in': f'state:{self.test_state_fips}',
            'key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if len(data) > 1:
                headers = data[0]
                county_data = data[1]
                
                # Calculate college-educated population
                college_educated = sum(int(county_data[i]) for i in range(1, 5))
                
                table = Table(title="Education Data")
                table.add_column("Education Level", style="cyan")
                table.add_column("Population", style="green")
                
                education_levels = ['Bachelor\'s', 'Master\'s', 'Professional', 'Doctorate']
                for i, level in enumerate(education_levels):
                    table.add_row(level, f"{int(county_data[i+1]):,}")
                
                table.add_row("Total College Educated", f"{college_educated:,}", style="bold")
                
                console.print(table)
                console.print(f"[green]✓ Successfully fetched education data[/green]")
                return data
            else:
                console.print("[red]✗ No data returned[/red]")
                return None
                
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗ Error fetching education data: {e}[/red]")
            return None
    
    def run_all_tests(self):
        """Run all Census API tests"""
        console.print(Panel.fit(
            "[bold green]US Census Bureau API Test Suite[/bold green]\n"
            f"Testing with County FIPS: {self.test_county_fips}\n"
            f"State FIPS: {self.test_state_fips}",
            title="Census API Tester"
        ))
        
        results = {}
        results['population'] = self.test_population_data()
        results['income'] = self.test_income_data()
        results['age_distribution'] = self.test_age_distribution()
        results['education'] = self.test_education_data()
        
        # Summary
        successful_tests = sum(1 for result in results.values() if result is not None)
        total_tests = len(results)
        
        console.print(f"\n[bold]Test Summary: {successful_tests}/{total_tests} tests passed[/bold]")
        
        if successful_tests == total_tests:
            console.print("[green]✓ All Census API tests passed![/green]")
        else:
            console.print("[yellow]⚠ Some tests failed. Check your API key and network connection.[/yellow]")
        
        return results

if __name__ == "__main__":
    tester = CensusAPITester()
    tester.run_all_tests()
