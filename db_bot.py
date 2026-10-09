import json
from openai import OpenAI
import os
import sqlite3
from time import time

print("Running db_bot.py!")

fdir = os.path.dirname(__file__)
def getPath(fname):
    return os.path.join(fdir, fname)

# SQLITE
sqliteDbPath = getPath("aidb.sqlite")
setupSqlPath = getPath("setup.sql")
setupSqlDataPath = getPath("setupData.sql")

# Erase previous db
if os.path.exists(sqliteDbPath):
    os.remove(sqliteDbPath)

# create new db
sqliteCon = sqlite3.connect(sqliteDbPath) 
sqliteCursor = sqliteCon.cursor()

# read in setup files
with (
        open(setupSqlPath) as setupSqlFile,
        open(setupSqlDataPath) as setupSqlDataFile
    ):

    setupSqlScript = setupSqlFile.read()
    setupSQlDataScript = setupSqlDataFile.read()

# execute setup files
sqliteCursor.executescript(setupSqlScript) # setup tables and keys
sqliteCursor.executescript(setupSQlDataScript) # setup tables and keys

def runSql(query):
    result = sqliteCursor.execute(query).fetchall()
    return result

# OPENAI
configPath = getPath("config.json")
print(configPath)
with open(configPath) as configFile:
    config = json.load(configFile)

openAiClient = OpenAI(api_key = config["openaiKey"])
openAiClient.models.list() # check if the key is valid (update in config.json)
chosen_model = "gpt-4o"

def getChatGptResponse(content):
    stream = openAiClient.chat.completions.create(
        model=chosen_model,
        messages=[{"role": "user", "content": content}],
        stream=True,
    )

    responseList = []
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            responseList.append(chunk.choices[0].delta.content)

    result = "".join(responseList)
    return result


# strategies
commonSqlOnlyRequest = " Give me a sqlite select statement that answers the question. Only respond with sqlite syntax. If there is an error do not explain it!"
strategies = {
    "zero_shot": setupSqlScript + commonSqlOnlyRequest,
    "single_domain_double_shot": (setupSqlScript +
                   " What bird has been seen the most? " +
                   " \nSELECT b.id, b.Name, COUNT(*) AS sighting_count\nFROM Bird b\nJOIN `Bird Sighting` bs ON b.id = bs.bird_id\nGROUP BY b.id, b.Name\nORDER BY sighting_count DESC\nLIMIT 1;\n " +
                   commonSqlOnlyRequest),
      "multi_domain_double_shot": (setupSqlScript +
                   " What bird has been seen the most? " +
                   " \nSELECT b.id, b.Name, COUNT(*) AS sighting_count\nFROM Bird b\nJOIN `Bird Sighting` bs ON b.id = bs.bird_id\nGROUP BY b.id, b.Name\nORDER BY sighting_count DESC\nLIMIT 1;\n " +
                   " What is the common name of the bird that birdwatcher_laura last saw? " +
                   " \nSELECT s.`common name`\nFROM `Bird Sighting` bs\nJOIN users u ON u.user_id = bs.person_id\nJOIN Bird b ON b.id = bs.bird_id\nJOIN Species s ON s.Species_id = b.Species_id\nWHERE u.username = 'birdwatcher_laura'\nORDER BY bs.`Sighting date` DESC, bs.sighting_id DESC\nLIMIT 1;\n " +
                   commonSqlOnlyRequest)
              
}

questions = [

    #"Who has seen the most individual birds",
    #"Who has been a user the longest",
    #"What was the common name of the last bird seen by Sydney_sky_spotter", #This one caused issues
    #"Is there a bird who has never been seen?",
    #"what bird has been seen by the widest amount of users?",
    #"What bird if any has been seen on a tuesday",
    "What species has the longest wingspan",
    #"What species in our database has the longest wingspan and what do they eat",
    #"What bird was seen last",
    #"what day of the week are more birds seen on"
]


# use the markdown for the sql syntax to find the SQL query
def sanitizeForJustSql(value):
    gptStartSqlMarker = "```"
    gptEndSqlMarker = "```"
    if gptStartSqlMarker in value:
        # Split at the first ``` and take everything after it
        value = value.split(gptStartSqlMarker, 1)[1]
        # Find the newline after the language identifier (sql, sqlite, etc.)
        newline_index = value.find("\n")
        if newline_index != -1:
            value = value[newline_index + 1:]
    if gptEndSqlMarker in value:
        # Split at the closing ``` and take everything before it
        value = value.split(gptEndSqlMarker, 1)[0]

    return value.strip()

for strategy in strategies:
    responses = {"strategy": strategy, "prompt_prefix": strategies[strategy]}
    questionResults = []
    print("########################################################################")
    print(f"Running strategy: {strategy}")
    for question in questions:

        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print("Question:")
        print(question)
        error = "None"
        try:
            getSqlFromQuestionEngineeredPrompt = strategies[strategy] + " " + question
            sqlSyntaxResponse = getChatGptResponse(getSqlFromQuestionEngineeredPrompt)
            sqlSyntaxResponse = sanitizeForJustSql(sqlSyntaxResponse)
            print("SQL Syntax Response:")
            print(sqlSyntaxResponse)
            queryRawResponse = str(runSql(sqlSyntaxResponse))
            print("Query Raw Response:")
            print(queryRawResponse)

            # TODO this prompt is insufficient. ChatGPT doesn't have all the context that it needs.
            # What context would help the friendly response be more successful? Can you fix it?
            friendlyResultsPrompt = "I asked a question \"" + question +"\" and the response was \""+queryRawResponse+"\" Please, just give a concise response in a more friendly way? Please do not give any other suggests or chatter. Use the data returned"
            friendlyResponse = getChatGptResponse(friendlyResultsPrompt)
            print("Friendly Response:")
            print(friendlyResponse)
        except Exception as err:
            error = str(err)
            print(err)

        questionResults.append({
            "question": question,
            "sql": sqlSyntaxResponse,
            "queryRawResponse": queryRawResponse,
            "friendlyResponse": friendlyResponse,
            "error": error
        })

    responses["questionResults"] = questionResults

    with open(getPath(f"response_{strategy}_{time()}.json"), "w") as outFile:
        json.dump(responses, outFile, indent = 2)


sqliteCursor.close()
sqliteCon.close()
print("Done!")
