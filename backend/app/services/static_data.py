# Static content data for the website
# In a real application, this might come from a CMS or database

services_data = [
    {
        "title": "Strategy Development", "icon": "fas fa-lightbulb",
        "description": "Navigate market shifts and achieve sustainable growth with future-proof strategies and organizational redesign.",
        "img_placeholder": "https://placehold.co/350x200/003087/FFFFFF?text=Strategy"
    },
    {
        "title": "Digital Transformation", "icon": "fas fa-rocket",
        "description": "Leverage cutting-edge technology, AI, and data analytics to optimize operations, enhance customer engagement, and build digital-native capabilities.",
        "img_placeholder": "https://placehold.co/350x200/007bff/FFFFFF?text=Digital"
    },
    {
        "title": "Performance and Cost Optimization", "icon": "fas fa-chart-line",
        "description": "Unlock hidden value through operational excellence, cost optimization, and process re-engineering for measurable bottom-line impact.",
        "img_placeholder": "https://placehold.co/350x200/6c757d/FFFFFF?text=Performance"
    }
]

clients_data = [
    {"name": "Global Tech Corp", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Global+Tech"},
    {"name": "Innovate Pharma", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Innovate"},
    {"name": "Quantum Finance", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Quantum"},
    {"name": "Apex Manufacturing", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Apex+Mfg"},
    {"name": "NextGen Retail", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=NextGen"},
    {"name": "Synergy Energy", "logo": "https://placehold.co/160x70/E0E0E0/6C757D?text=Synergy"}
]

testimonials_data = [
     {
        "quote": "SynergyPro's insights into digital transformation were instrumental in reshaping our customer experience and driving significant growth. Their team is world-class.",
        "author": "Eleanor Vance",
        "title": "Chief Technology Officer, Global Tech Corp"
     },
     {
        "quote": "The operational efficiency program designed by SynergyPro delivered results beyond our expectations, streamlining processes and improving our bottom line.",
        "author": "Kenji Tanaka",
        "title": "VP Operations, Apex Manufacturing"
     },
     {
        "quote": "Their strategic guidance helped us navigate a complex market entry. We felt supported and confident with SynergyPro as our partner.",
        "author": "Aisha Khan",
        "title": "Head of Strategy, Innovate Pharma"
     }
]

hero_content = {
    "headline": "Shape Your Future. Achieve Outstanding Results.",
    "subheadline": "Partnering with leaders to solve their toughest challenges and capture their greatest opportunities through strategic insight and digital innovation.",
    "cta_button_text": "Discover Our Solutions", "cta_link": "#services",
    "background_image_placeholder": "https://source.unsplash.com/1600x900/?business,technology,abstract"
}

products_data = [
    {
        "id": "prod_ai_analyzer",
        "name": "AI Financial Analyzer",
        "tagline": "Unlock insights from your financial data.",
        "description": "Upload your P&L or other statements (.xlsx, .csv, .docx, .txt) for automated insights and conceptual SWOT analysis. (Beta)",
        "img_placeholder": "https://placehold.co/350x200/0056b3/FFFFFF?text=AI+Analyzer",
        "link": "/financial-analyzer" # Changed link for new page
    },
    {
        "id": "prod_startup_consult",
        "name": "Startup Consultation AI",
        "tagline": "Get AI-driven feedback for your venture.",
        "description": "Input key metrics about your startup for AI consultation on strategy, risks, opportunities, and valuation factors. Includes placeholder reports & case studies. (Beta)",
        "img_placeholder": "https://placehold.co/350x200/17a2b8/FFFFFF?text=Startup+AI",
        "link": "/startup-consultation" # Changed link for new page
    },
    {
        "id": "prod_custom_solution",
        "name": "Custom Consulting Solutions",
        "tagline": "Tailored strategies for your unique challenges.",
        "description": "Leverage our expert consultants for bespoke solutions in strategy, digital transformation, performance optimization, and more. Contact us.",
        "img_placeholder": "https://placehold.co/350x200/ffc107/000000?text=Custom",
        "link": "/custom-consulting" # Link to contact section on main page
    }
]
custom_consulting_packages = [
    {
        "id": "tech_dd",
        "name": "Technology Due Diligence",
        "description": "Our areas of concentration cover the team, the product, platform architecture and the infrastructure of the target company highlighting possible issues that could put our clients at risk. Our goal is to remain unbiasedly identify potential risks and offer insights that allow clients to make the best decisions.",
        "deliverables": [
            "Technical assessment overview",
            "Technology and Architecture review",
            "Platform Scalability analysis",
            "Code review and quality assessment",
            "Infrastructure and DevOps assessment",
            "Product and UX/UI review/assessment", # Combined for brevity
            "Customer surveys",
            "Risk assessment",
            "Action Plan"
        ],
        "documents": [
            "Executive Summary containing impactful information from the insights gathered through overall technical due diligence that influence summary findings.",
            "Data databook outlining detailed data points and data management plan as well as supporting documentation.",
            "Action items and points having a comprehensive list of areas that require improvement from the product/service offered and technology and changes for improvement in the digital strategy."
        ],
        "icon": "fas fa-cogs" # Example icon
    },
    {
        "id": "cdd",
        "name": "Commercial Due Diligence (CDD)",
        "description": "CDD provides the client with a comprehensive understanding of the target company's commercial position, market dynamics, and growth prospects. They enable the client to assess the attractiveness of the deal, independently evaluate potential synergies, and make informed decisions regarding the transaction.",
        "deliverables": [
            "Market Analysis Report",
            "Competitive Landscape Assessment",
            "Customer Analysis",
            "Revenue and Financial Analysis",
            "Management/Team Assessment", # Combined/simplified
            "Team Capabilities",
            "Growth Strategy",
            "Commercial Due Diligence Summary",
            "Action plan"
        ],
        "documents": [
            "Detailed report containing detailed investment thesis with outputs driven from completed data points (interviews, surveys, analysis and report).",
            "Complete Databook containing all insights gathered via the CDD engagement.",
            "Executive summary marketing financial outputs captured from the steps followed in the engagement including summary financials. (Length can vary 5-10 pages).",
            "Excel file work outlining detailed financial and operational plan as well as having data models showing revenue and financial analysis, business valuation summary and output.",
            "Action items and pain points having a comprehensive list of areas that require improvement from the product/service offered and technology and changes for improvement."
        ],
         "icon": "fas fa-briefcase"
    },
    {
        "id": "investor_pres",
        "name": "Investor Presentation",
        "description": "Our investor presentation service help you position business right before investor and raise your next funding round.",
        "deliverables": [
            "Pitch Deck Audit",
            "Executive Summary",
            "Value Proposition",
            "Market Analysis",
            "Product Strategy",
            "Business Model and Revenue Generation",
            "Financial Projections",
            "Fundraising Strategy",
            "Use of Funds",
            "Action plan"
        ],
        "documents": [
            "Investment Thesis outlining investment hypothesis and quantitative estimation of the the opportunity size covering TAM, SAM, SOM.",
            "An Investor pitch deck containing information about company overview, market, product/service description, analysis, unique selling points, business model analysis as well as revenue generation plans (Length 20-25 pages).",
            "An action plan containing each databook providing detailed financial projections, detailed revenue structure, expense projections and cash flow analysis."
        ],
         "icon": "fas fa-file-powerpoint"
    },
    {
        "id": "gtm_strategy",
        "name": "Go To Market Strategy",
        "description": "The goal of GO TO MARKET research is to develop a comprehensive plan that maximises the chances of success for a new product or service while minimizing the risk of failure.",
        "deliverables": [
            "Business Analysis",
            "Market Research and Analysis",
            "Customer Segmentation and Targeting",
            "Competitive Benchmarking",
            "Marketing and Sales Strategy/Framework", # Combined
            "Pricing and operational model/support Plan", # Combined
            "Metrics and KPIs",
            "GTM Plan Executive Summary"
        ],
        "documents": [
            "Detailed GTM strategy report containing identifiable outputs driven from comprehensive business analysis, market research and analysis report.",
            "A complete data book from the marketing and sales outlining the framework (About 30-40 pages depending on the engagement).",
            "A complete financial model outlining the marketing and sales team budget and deep dive financial analysis as well as overall cost analysis and market prioritization report (15-20 Pages).",
            "Action plan documents having a detailed pricing and operational launch plan, metrics as well as having data models showing critical financial metrics and KPIs.",
            "Action items and pain points having a comprehensive list of areas that require improvement from the product/service offered and technology and changes for improvement in the overall business strategy."
        ],
         "icon": "fas fa-rocket"
    },
    {
        "id": "fin_modeling",
        "name": "Financial Modeling",
        "description": "Financial data and calculations can be used for purposes such as valuation, budgeting, forecasting, risk management, financial planning, and investment analysis.",
        "deliverables": [
            "Financial Model for startup fundraising",
            "M&A Modeling",
            "Functional Budgeting & KPIs",
            "Operational Modeling",
            "Cash Flow Analysis",
            "Valuation Modeling",
            "Financial KPIs",
            "Investor Report (incl. Model)",
            "Financial Presentation to Board"
        ],
        "documents": [
            "An excel file containing each databook providing detailed projection of the financial structure along with sensitivity analysis. Model output includes revenue forecast, expense projections, and cash flow analysis.",
            "Financial model output including 3-statement financial model with discount, WACC assumption, Multiples, DCF, IRR and ARR as well as other financial metrics.",
            "Detailed Financial plan containing Financial highlights and narrative. (10-15 pages)."
        ],
         "icon": "fas fa-calculator"
    },
     {
        "id": "cap_table",
        "name": "Cap Table Simulation",
        "description": "A Cap Table simulation analyzes different funding scenarios.", # Simplified description
        "deliverables": [
            "Cap table Simulation Report",
            "Waterfall Analysis (incl. Sensitivity Analysis)",
            "Shareholder Analysis",
            "Investor Analysis",
            "Valuation Assessment",
            "Sensitivity Analysis",
            "Final output"
        ],
        "documents": [
            "Detailed cap table with scenarios.",
            "Convertible debt/equity simulation document to capture investment amount, valuation cap, discount & interest, issued/unissued shares to round.",
            "Leading ESOP simulation.",
            "Profit sharing distribution model based on pre/post round valuation assumptions."
        ],
         "icon": "fas fa-table"
    },
    {
        "id": "ux_audit",
        "name": "UX Audit Service",
        "description": "Our areas of concentration are product, team, platform understanding and the infrastructure. Highlighting possible issues that could put our clients at risk. Our goal is to remain unbiasedly identify potential risks and offer insights that allow clients to make the best decisions.", # Description seems similar to Tech DD, adjust if needed
        "deliverables": [
            "Platform Understanding",
            "User Workflow Analysis/Maps", # Combined
            "Heuristic Evaluation",
            "Accessibility (WCAG) Analysis",
            "Customer Journey Mapping",
            "User Testing",
            "Final output",
            "Action Plan"
        ],
        "documents": [
            # Assuming similar output types to Tech DD but focused on UX
            "Executive Summary of UX findings and strategic recommendations.",
            "Detailed UX Audit Report outlining issues, heuristics violations, accessibility gaps.",
            "User journey maps and workflow analysis documentation.",
            "User testing results synthesis.",
            "Prioritized action plan for UX improvements."
        ],
         "icon": "fas fa-search-plus"
    }
    # Add more packages as needed
]