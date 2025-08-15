# RCA Agent with Business Logic Evaluation

## Overview

The RCA (Root Cause Analysis) Agent has been enhanced to include **business logic evaluation** as part of its diagnostic process. This means that when the RCA agent analyzes a failure, it not only identifies the technical root cause but also evaluates the current business logic against test cases to understand the full scope of the issue.

## Key Features

### 🔍 **Integrated Business Logic Evaluation**
- **Automatic Test Execution**: Runs relevant test cases when analyzing failures
- **Failure Pattern Analysis**: Identifies common failure patterns across tests
- **Business Impact Assessment**: Evaluates the business impact of failures
- **Actionable Recommendations**: Generates specific recommendations for fixes

### 🧪 **Test Case Management**
The RCA agent includes predefined test cases for:
- **Return Policy Validation**: Tests return policy business logic
- **Schema Validation**: Tests data schema completeness
- **Business Rule Compliance**: Tests critical business rules

### 📊 **Evaluation Results**
Each evaluation provides:
- Test execution results with pass/fail status
- Detailed failure analysis (missing fields, type mismatches, rule violations)
- Business impact assessment (customer experience, revenue impact, operational impact)
- Specific recommendations with effort estimates and file locations

## How It Works

### 1. **Failure Detection**
When a `RETURN_API_FAILURE` event occurs, the RCA agent:
- Receives the failure event
- Extracts the trace step information
- Triggers business logic evaluation

### 2. **Business Logic Evaluation**
The agent automatically:
- Runs relevant test cases based on the failure type
- Simulates the failing business logic
- Compares actual vs. expected results
- Identifies specific failure patterns

### 3. **Enhanced RCA Analysis**
The evaluation results are integrated into the RCA process:
- More detailed failure analysis
- Better understanding of business impact
- More targeted patch recommendations
- Improved confidence in the diagnosis

## Example Workflow

```
1. API Failure Occurs
   ↓
2. RCA Agent Receives Failure Event
   ↓
3. Business Logic Evaluation Triggered
   ↓
4. Test Cases Executed
   ↓
5. Failure Patterns Analyzed
   ↓
6. Business Impact Assessed
   ↓
7. Enhanced RCA Plan Generated
   ↓
8. Specific Recommendations Provided
```

## Test Cases Included

### Return Policy Validation
- **Valid Return Policy**: Tests successful return policy retrieval
- **Missing Return Policy**: Tests failure case for missing policy data

### Schema Validation
- **Complete Product Data**: Tests complete product schema
- **Incomplete Product Data**: Tests missing required fields

## Business Impact Assessment

The agent evaluates failures across multiple dimensions:
- **Customer Experience**: Good/Degraded/Poor
- **Revenue Impact**: None/Medium/High
- **Operational Impact**: Low/Medium/High
- **Compliance Risk**: Low/Medium/High
- **Estimated Downtime**: Based on failure severity

## Recommendations Generated

The agent provides specific, actionable recommendations:
- **Priority Level**: Critical/High/Medium/Low
- **Action Required**: Specific steps to take
- **Effort Estimate**: Time required for implementation
- **Files to Modify**: Specific code locations to change

## Usage

### Running the Enhanced RCA Agent

```python
from agents.rca_agent import RCAAgent

# Initialize the agent
rca_agent = RCAAgent()

# Start monitoring for failures
await rca_agent.start()

# The agent will automatically:
# - Monitor for RETURN_API_FAILURE events
# - Run business logic evaluation
# - Provide enhanced RCA analysis
```

### Testing the Evaluation

Use the provided test script:
```bash
python3 test_rca_evaluation.py
```

This will demonstrate the enhanced RCA capabilities with sample failure scenarios.

## Benefits

### 🎯 **Better Problem Diagnosis**
- More comprehensive failure analysis
- Business context for technical issues
- Pattern recognition across multiple failures

### 🚀 **Faster Resolution**
- Specific, actionable recommendations
- Effort estimates for fixes
- File locations for changes

### 📈 **Business Understanding**
- Impact assessment for stakeholders
- Risk evaluation for prioritization
- Customer experience implications

### 🔧 **Proactive Prevention**
- Pattern identification for future issues
- Recommendations for system improvements
- Business rule validation

## Integration Points

The enhanced RCA agent integrates with:
- **Event Bus**: Monitors failure events
- **Business Logic**: Evaluates current functionality
- **Patch Generation**: Provides context for fixes
- **Verification**: Includes evaluation results in analysis

## Future Enhancements

Potential improvements include:
- **Dynamic Test Case Generation**: Based on failure patterns
- **Machine Learning**: Pattern recognition and prediction
- **Performance Metrics**: Evaluation execution time and accuracy
- **Custom Test Cases**: User-defined business logic tests
- **Integration with CI/CD**: Automated evaluation in deployment pipeline

## Conclusion

The enhanced RCA agent now provides a comprehensive approach to failure analysis by combining technical root cause analysis with business logic evaluation. This results in better problem understanding, faster resolution, and improved system reliability. 