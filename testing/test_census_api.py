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
import pytest

# Load environment variables
load_dotenv()

console = Console()

@pytest.fixture(scope="module")
def tester():
    return CensusAPITester()

class CensusAPITester:
    def __init__(self):
        self.api_key = os.getenv('CENSUS_API_KEY')
        self.base_url = 'https://api.census.gov/data'
        self.test_county_fips = os.getenv('TEST_COUNTY_FIPS', '06085')  # Santa Clara County, CA
        self.test_state_fips = os.getenv('TEST_STATE_FIPS', '06')  # California
        
        if not self.api_key:
            pytest.fail("CENSUS_API_KEY not found in environment variables")
        else:
            console.print(f"[green]CENSUS_API_KEY loaded: {self.api_key}[/green]")

def test_population_data(tester):
    """Test fetching population data for a county"""
    console.print("\n[bold blue]Testing Population Data Fetch[/bold blue]")
    
    # ACS 5-Year Data for 2022
    url = f"{tester.base_url}/2022/acs/acs5"
    params = {
        'get': 'NAME,B01003_001E',  # Total population
        'for': f'county:{tester.test_county_fips}',
        'in': f'state:{tester.test_state_fips}',
        'key': tester.api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        if response.status_code == 204:
            console.print("[yellow]✗ No content returned from API (204)[/yellow]")
            pytest.skip("No content returned from API (204)")

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
            assert True
        else:
            console.print("[red]✗ No data returned[/red]")
            assert False, "No data returned"
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]✗ Error fetching population data: {e}[/red]")
        assert False, f"Request failed: {e}"

def test_income_data(tester):
    """Test fetching median household income data"""
    console.print("\n[bold blue]Testing Income Data Fetch[/bold blue]")
    
    url = f"{tester.base_url}/2022/acs/acs5"
    params = {
        'get': 'NAME,B19013_001E',  # Median household income
        'for': f'county:{tester.test_county_fips}',
        'in': f'state:{tester.test_state_fips}',
        'key': tester.api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        if response.status_code == 204:
            console.print("[yellow]✗ No content returned from API (204)[/yellow]")
            pytest.skip("No content returned from API (204)")

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
            assert True
        else:
            console.print("[red]✗ No data returned[/red]")
            assert False, "No data returned"
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]✗ Error fetching income data: {e}[/red]")
        assert False, f"Request failed: {e}"

def test_age_distribution(tester):
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
    
    url = f"{tester.base_url}/2022/acs/acs5"
    params = {
        'get': f'NAME,{",".join(age_variables)}',
        'for': f'county:{tester.test_county_fips}',
        'in': f'state:{tester.test_state_fips}',
        'key': tester.api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        if response.status_code == 204:
            console.print("[yellow]✗ No content returned from API (204)[/yellow]")
            pytest.skip("No content returned from API (204)")

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
            assert True
        else:
            console.print("[red]✗ No data returned[/red]")
            assert False, "No data returned"
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]✗ Error fetching age distribution data: {e}[/red]")
        assert False, f"Request failed: {e}"

def test_education_data(tester):
    """Test fetching educational attainment data"""
    console.print("\n[bold blue]Testing Education Data Fetch[/bold blue]")
    
    # Educational attainment variables
    education_variables = [
        'B15003_022E',  # Bachelor's degree
        'B15003_023E',  # Master's degree
        'B15003_024E',  # Professional degree
        'B15003_025E',  # Doctorate degree
    ]
    
    url = f"{tester.base_url}/2022/acs/acs5"
    params = {
        'get': f'NAME,{",".join(education_variables)}',
        'for': f'county:{tester.test_county_fips}',
        'in': f'state:{tester.test_state_fips}',
        'key': tester.api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        if response.status_code == 204:
            console.print("[yellow]✗ No content returned from API (204)[/yellow]")
            pytest.skip("No content returned from API (204)")

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
            assert True
        else:
            console.print("[red]✗ No data returned[/red]")
            assert False, "No data returned"
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]✗ Error fetching education data: {e}[/red]")
        assert False, f"Request failed: {e}"

@pytest.mark.xfail(reason="B24050 variables may not be available for 2022 ACS 5-year data at the county level")
def test_housing_poverty_employment_data(tester):
    """Test fetching housing, poverty, and employment data"""
    console.print("\n[bold blue]Testing Housing, Poverty, and Employment Data Fetch[/bold blue]")
    
    # Housing, Poverty, and Employment variables
    variables = [
        'B25002_001E',  # Total Housing Units
        'B17001_002E',  # Poverty Status in the Past 12 Months: Below poverty level
        'B24050_001E',  # Total Civilian Employed Population 16 Years and Over
        'B24050_003E',  # Management, business, science, and arts occupations
        'B24050_007E',  # Service occupations
        'B24050_011E',  # Sales and office occupations
    ]
    
    url = f"{tester.base_url}/2022/acs/acs5"
    params = {
        'get': f'NAME,{",".join(variables)}',
        'for': f'county:{tester.test_county_fips}',
        'in': f'state:{tester.test_state_fips}',
        'key': tester.api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        if response.status_code == 204:
            console.print("[yellow]✗ No content returned from API (204)[/yellow]")
            pytest.skip("No content returned from API (204)")
            
        data = response.json()
        
        if len(data) > 1:
            headers = data[0]
            county_data = data[1]
            
            table = Table(title="Housing, Poverty, and Employment Data")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            
            for i, header in enumerate(headers):
                if i == 0:  # Skip NAME
                    continue
                table.add_row(headers[i], f"{int(county_data[i]):,}" if county_data[i].isdigit() else str(county_data[i]))
            
            console.print(table)
            console.print(f"[green]✓ Successfully fetched housing, poverty, and employment data[/green]")
            assert True
        else:
            console.print("[red]✗ No data returned[/red]")
            assert False, "No data returned"
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]✗ Error fetching housing, poverty, and employment data: {e}[/red]")
        assert False, f"Request failed: {e}"
