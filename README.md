# CONTENT
 - [Quick Introduction](#quick-introduction)
 - [I can boast about](#i-can-boast-about)
 - [Introduction to users](#introduction-to-users)
 - [Quickstart](#quickstart)
 - [Introduntion to developers](#introduntion-to-developers)
 - [Full Guide](#full-guide)
 - [Evaluations](#evaluations)


# Quick Introduction
1. Get a review for your code changes before pushing it to production or taking valuable time of senior engineer to catch rokie mistakes
2. see a graphical visualisation of your repository

# I can boast about 
 * I have built the fastest codebase graph builder for python codebases using  ```ast``` that can build a graph of 1000 nodes in less than 5 seconds.

# Introduction to users
1. **How this Agentic reviewer works:** it converts the whole repo into an directed graph with nodes named as their ```fqn``` that is used later to grab the right context, it detectcts the newly added or modified nodes(any classes, methods, functions are nodes and can be in any level of nesting) then it grabs whole defination of the changed entity by anlysing ```git diff``` then using graph it grabs all the nodes that are either used inside of the node in sunject or nodes that are using it(simply put all the nodes that are connected by ```calls``` and ```called_by``` edges to the node in subject) then various agents will work as expertes in various domains and they scritanize the code in their respective domains. By default we have three experts set up
    1. ```LOGIC``` critic 
    2. ```ARCHITECTURE``` critic 
    3. ```SECURITY``` critic

2. Currently it ```only supports python``` codebases but will adding support for  more languages in future updates.

# Quickstart
1. **Clone** the repo locallaly
2. **Delete** ```evaluations/```, ```logs/```, ```reports/```, ```.gitignore``` you dont need them they are leftovers of my trail runs.
3. **Graph visualization** NOTE: currently only works for python codebases.
    ```python
    if __name__ == "__main__":
        from codebase_map import launch_gui
        from pathlib import Path
        
        project_path = r'../document_align'
        project_path = r'../huggingface_transformer_clone/transformers/src/transformers/generation'
        project_path = r'../buggy_fintech_portfolio_manager'
        absolute_path = Path(project_path).absolute().resolve()

        launch_gui(absolute_path)
    ```
    ![Repo Graph Visualization Image](media_assets/repo_graph.png)
4. **Code Review** 
    ```python
    from pathlib import Path

    from agentic_code_reviewer.clients import (
        OpenAIClient,
        GeminiClient,
        GroqClient,
        MistralClient,
        CerebrasClient,
        OpenRouterClient
    )
    from agentic_code_reviewer.my_langgraph import create_code_review_agent, default_code_review_agent
    from agentic_code_reviewer.paths import REPORTS_DIR_PATH


    project_path = r'../document_align'
    project_path = r'../huggingface_transformer_clone/transformers/src/transformers/generation'
    project_path = r'../buggy_fintech_portfolio_manager'

    absolute_path = Path(project_path).resolve()
    
    client = GeminiClient()
    # client = OpenAIClient()
    # client = GroqClient()
    # client = MistralClient()
    # client = CerebrasClient()
    # client = OpenRouterClient()
    
    agent = default_code_review_agent(client=client)
    
    final_state = run_code_review(
        agent=agent,
        absolute_project_path=project_path,
        report_dir=REPORTS_DIR_PATH / f"{client.__class__.__name__}_reports",
        require_linter=False
    )
    ```

# Introduntion to developers
1. **How this Agentic reviewer works:**
    * **Context Grabing:** 
        * **Code Context:** Well, to find an issue, it is not enough to check, analyze only the changed function block. That function is being called many places, and that function also uses another functions. The issue can arrive in any of these levels. There is no hard limit how deep up and how deep down we should go in this call graph. But for our convenience here and to minimize the context, we are only going to analyze the first child and first parent of the changed function.
        * **Codebase Context:** For simple hobby projects and portfolio projects, only using code context may be enough. But for slightly larger and complex code bases, we almost certainly need a bird's eye view of the code base, like what actually this code base is trying to solve, what is the file structure, and what each file and package is responsible for. So it is advised that a proper context of code base that user wants to review should be placed in that directory. If it is present, this reviewer, this agentic reviewer will grab it automatically. If it is not, it will just print a warning in the terminal.
        * **Linter Context:** You are seeing your agentic code reviewer is doing the job of a linter. So, and wasting your tokens and compute. In that case, we will provide the linter report in the context and instruct the agent that it must not point out this linter findings as it is already been discovered. This works perfectly, but it increases the prompt tokens massively. So use it wisely. It is advised that before reviewing your code base, first run a linter client on your code base and fix all of that that a linter is complaining.
    * **Agent Workflow:** 
        * **Agent Creation:** All the agents, as may be required by the use case. For example, security logic architecture can be created, and all of these agents will get the above context and then produce a structured output. This output, then further processed by an arbitrator agent. Arbitrator agent does not use any language model for its processing. It is purely logic-based. It filters the issues by using their confidence and creates a beautiful Markdown report from the findings of individual critics. It uses Langgraph.
        ```mermaid
        flowchart TD
            A[Context] --> B[Expert1]
            A --> C[Expert2]
            A --> D[Expert3]
            A --> E[Expert4]
            B --> F[Arbitrator]
            C --> F
            D --> F
            E --> F
            F --> G[Markdown Report]

    * **Observation:** For every single run, the complete prompt and the response is duly noted in the log files. These log files are named same as their critic name. We can always go and check it if anything goes wrong. Number of tokens consumed and the model used is also stored, so the user can monitor them very easily. [Example Log File](logs/logic_critic.log)
    * **Features:** 
        * **Graphical Visualization of the Codebase:** graph of our code base that we built to grab the proper context. We can also use that to visualize the code base in the browser using streamlit.
        * **Custom Agents:** We can employ as many experts as we need. To create those experts or agents, we need to supply the system prompt, how they should behave, and name, what is the name of this particular critic and the client with a particular model selected.
        * **Available Clients:** The following clients are available for use:
            * OpenAI
            * Gemini
            * Groq
            * Mistral
            * Cerebras
            * OpenRouter
        * **Supported Models:** Ypu can use any model that a particular client is providing, but I have also made a model registry that you can see by this method. See the ```ClientInterface``` for more features.
            ```python
            from agentic_code_reviewer.clients import (
                    ClientInterface,
                    OpenAIClient,
                    GeminiClient,
                    GroqClient,
                    MistralClient,
                    CerebrasClient,
                    OpenRouterClient
                )
            ClientInterface.show_all_models()
            # OR
            GeminiClient.show_models()

            client = GeminiClient()
            #OR
            client = GeminiClient(model_name="gemini-3.5-flash")
            ```
        
# Full Guide
1. **Installation**
    * **Clone** the repo locallaly
    * **Delete** ```evaluations/```, ```logs/```, ```reports/```, ```.gitignore``` you dont need them they are leftovers of my trail runs.
    * **Install** the dependencies using pip
        ```bash
        pip install -r requirements.txt
        ```
2. **Graph visualization** NOTE: currently only works for python codebases.
    If there are too many nodes in the graph, it may take a while to load the graph in the browser. It is advised to use a smaller codebase for this feature. A hard limit of 2000 nodes is set for this feature. If the codebase has more than 2000 nodes, it will not be visualized in the browser. It will just print a warning in the terminal.
    ```python
    from codebase_map import launch_gui
    from pathlib import Path
    
    project_path = r'../document_align'
    project_path = r'../huggingface_transformer_clone/transformers/src/transformers/generation'
    project_path = r'../buggy_fintech_portfolio_manager'
    absolute_path = Path(project_path).absolute().resolve()

    launch_gui(absolute_path)
    ```
    ![Repo Graph Visualization Image](media_assets/repo_graph.png)
3. **Code Review** 
    ```python
    from pathlib import Path


    from agentic_code_reviewer import (
        create_code_review_agent, default_code_review_agent,
        run_code_review,
        OpenAIClient,
        GeminiClient,
        GroqClient,
        MistralClient,
        CerebrasClient,
        OpenRouterClient,
        AgentFactory
    )
    from agentic_code_reviewer.paths import REPORTS_DIR_PATH

    project_path = r'../document_align'
    project_path = r'../huggingface_transformer_clone/transformers/src/transformers/generation'
    project_path = r'../buggy_fintech_portfolio_manager'

    absolute_path = Path(project_path).resolve()
    
    client = GeminiClient()
    # client = OpenAIClient()
    # client = GroqClient()
    # client = MistralClient()
    # client = CerebrasClient()
    # client = OpenRouterClient()
    
    agent = default_code_review_agent(client=client)
    
    final_state = run_code_review(
        agent=agent,
        absolute_project_path=project_path,
        report_dir=REPORTS_DIR_PATH / f"{client.__class__.__name__}_reports",
        require_linter=False
    )
4. **Make Custom Agents:** We can employ as many experts as we need. To create those experts or agents, we need to supply the system prompt, how they should behave, and name, what is the name of this particular critic and the client with a particular model selected.
    ```python
    from agentic_code_reviewer import (
        OpenAIClient,
        GeminiClient,
        GroqClient,
        MistralClient,
        CerebrasClient,
        OpenRouterClient,
        create_code_review_agent,
        AgentFactory
    )

    gemini_client = GeminiClient()
    openai_client = OpenAIClient()
    # groq_client = GroqClient()
    # mistral_client = MistralClient()
    # cerebras_client = CerebrasClient()
    # openrouter_client = OpenRouterClient()

    expert1_name = "expert1"
    expert1_category = "expert1_category"
    expert1_sys_prompt = "expert1 system prompt"
    expert2_name = "expert2"
    expert2_category = "expert2_category"
    expert2_sys_prompt = "expert2 system prompt"
    expert3_name = "expert3"
    expert3_category = "expert3_category"
    expert3_sys_prompt = "expert3 system prompt"
    expert4_name = "expert4"
    expert4_category = "expert4_category"
    expert4_sys_prompt = "expert4 system prompt"

    agent_factories = [AgentFactory(
                        name=name, 
                        category=category, 
                        system_prompt=system_prompt, 
                        client=openai_client
                        ) 
                        for name, category, system_prompt in 
                        [(expert1_name, expert1_category, expert1_sys_prompt),
                        (expert2_name, expert2_category, expert2_sys_prompt),
                        (expert3_name, expert3_category, expert3_sys_prompt),
                        (expert4_name, expert4_category, expert4_sys_prompt)]
    ]
    ```

# Evaluations
For evaluation, I have tried two methods. First, I tried that. First, I tried that I will evaluate any large GitHub repository which is in Python and also open source GitHub Python library which is used extensively and maintained regularly. So I tried to run evaluations on Hugging Face Transformers repository. I have designed all the tools to extract the ground truth. Like ground truth, I am extracting from comments of contributor and maintainer, commit comments, and their specific code selection that they are commenting on. And by that, I thought this will serve as ground truth for the evaluation. But turns out those comments are not very descriptive. Most of the time it is like done, and any short form. But the main problem with this repository was that the maintainer and the contributor didn't claim any logical, straightforward issues in the code base that can be, like most of the time. It is very rarely in the GitHub repository of that standard and that scale that any real bug and issue security risk is exposed like that. Most of the time they are just minor architectural improvements and adding support to new model or framework like this. Agent code reviewer at this stage cannot identify those issues that human collaborator and maintainer can, because much of the issues that they are trying to solve is the compatibility with other services. So in the current code base there is no ground truth or context of those external services. That's why this GitHub approach did not and provide fruitful result. So I decided to make an extensive [Dummy Fintech Portfolio Manager Repository](https://github.com/RHMTshaikh/buggy_fintech_portfolio_manager.git) and intentionally add bugs in it and watch if the agent reviewer can catch. I built a fintech portfolio manager and intentionally left many kinds of and many levels of and various difficulty levels of issues. The complete repository, this dummy repository, is also published on GitHub. You can see it here, and you can also find the issues that I have introduced in it. I have made eight branches of this dummy repository, and in each branches I have introduced three to five issues. Not only issues, I have also introduced non-critical changes so that I can test my model on false positive cases.

Evaluation Results: The evaluation results are stored in the ```evaluations/``` directory.   
See --> [Evaluation Results](evaluations/gemini-3.5-flash-lite/name_buggy_fintech_portfolio_manager/branch_accounting-ledger-update.log)  
See --> [Evaluation Scores](evaluations/evaluation_scores.json)  

**Structure of Evaluation Data**

```Python
class EvaluationScores(BaseModel):
    """Nested schema for the detailed evaluation scores."""
    model_config = {"extra": "forbid"}
    
    recall: int = Field(description="Score from 0 to 4 based on the number of ground truth issues successfully found.")
    root_cause: int = Field(description="Score from 0 to 3 evaluating if the systemic impact was correctly explained according to the repository context.")
    false_positive_penalty: int = Field(description="Penalty from -3 to 0 for falsely flagging benign code changes as critical bugs.")
    hallucination_penalty: int = Field(description="Penalty from -2 to 0 for inventing code not present in the diff or asserting fake bugs.")
    actionability: int = Field(description="Score from 0 to 2 evaluating if the remediation steps are clear, correct, and safe to apply.")
    discovery_bonus: int = Field(description="Bonus from 0 to 2 for identifying legitimate, severe flaws that were not listed in the Ground Truth.")

class FindingEvaluation(BaseModel):
    model_config = {"extra": "forbid"}

    original_review_finding_identifier: str = Field(description="Unique identifier description of the issue found by the review agent.")
    issue_id: Optional[int] = Field(description="Issue ID of the corresponding ground truth issue if it was successfully matched. None if not detected.")
    severity_correct: Optional[bool] = Field(description="Whether the severity level was correctly assessed. None if not detected.")
    category_correct: Optional[bool] = Field(description="Whether the category was correctly assessed. None if not detected.")
    description_correct: Optional[bool] = Field(description="Whether the description of issue correctly represents the problem described in the ground truth.")
    remediation_quality: Optional[str] = Field(description="Assessment of the suggested remediation steps. None if not detected.")
    false_positive_flagged: bool = Field(description="Whether the agent incorrectly flagged a safe, benign change as a bug.")

class EvaluatorResponse(BaseModel):
    """The strict JSON schema the LLM must follow when evaluating the agent."""
    model_config = {"extra": "forbid"}
    
    finding_evaluations: list[FindingEvaluation]
    missed_ground_truths_ids: list[int] = Field(description="List of issue IDs of the ground truth issues that the agent failed to identify.")
    reasoning: str = Field(description="Step-by-step logical breakdown of the comparison before scoring.")
    score: EvaluationScores = Field(description="The overall evaluation scores.")
```

## Scores
* **Review Agent:** openai/gpt-oss-120b
* **Ground Truth Repository:** [Dummy Fintech Portfolio Manager](https://github.com/example/dummy-fintech-portfolio-manager)
* **Evaluation Agent:** Gemini-3.5-flash-lite
* **Scores for all branches**
    * **recall**: [2, 0, 3, 0, 0, 4, 2, 2, 1]
    * **root_cause**: [2, 0, 2, 0, 0, 3, 2, 2, 2]
    * **false_positive_penalty**: [ -2, -1, 0, 0, -1, 0, -1, -1, -2]
    * **hallucination_penalty**: [0, 0, 0, 0, 0, 0, 0, 0, 0]
    * **actionability**: [2, 1, 2, 0, 1, 2, 2, 2, 2]
    * **discovery_bonus**: [0, 0, 0, 0, 0, 0, 0, 0, 0]
* **Average Scores**
    | parameter | value | range |
    |-----------|-------|-------------|
    |**recall**| 1.56 | 0 - 4 |
    |**root_cause**| 1.44 | 0 - 3 |
    |**false_positive_penalty**| -0.89 | -3 - 0  |
    |**hallucination_penalty**| 0.0 | -2 - 0|
    |**actionability**| 1.56 |  0 - 2 |
    |**discovery_bonus**| 0.0 |  0 - 2|
    |**Overall Score**| 7.37 | -5 - 11 |

    **Which amounts to 77% of the maximum possible score.**
