# Setting up Microsoft Foundry

InsideMatch uses a model deployed in **Microsoft Foundry** to write grounded insights and recaps. Without it, the app
runs fully on the clearly-labeled mock provider (`AI_PROVIDER=mock`).

Verified against Microsoft Learn on 2026-10-23:
[create projects](https://learn.microsoft.com/en-us/azure/foundry/how-to/create-projects) (2026-09-25),
[deploy Foundry models](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/deploy-foundry-models) (2026-07-28),
[endpoints](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/endpoints) (2026-10-19),
[v1 API](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle) (2026-06-05),
[structured outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs) (2026-08-24).

## 1. Create a project

1. Sign in at <https://ai.azure.com> and make sure the **New Foundry** toggle is on.
2. Select the project name in the upper-left corner, then **Create new project**.
3. Name it (e.g. `insidematch`) and select **Create project**. Under advanced options you can pick a **Resource group**
   (a new one is simplest) and a **Location**. The portal creates the Foundry resource for you.

You need a role such as **Foundry Account Owner** or **Foundry Owner** on the subscription or resource group.

## 2. Deploy a model

1. Select **Discover** (upper right), then **Models** (left pane).
2. Find **gpt-4.1-mini** (version `2025-04-14` supports structured outputs). `gpt-4.1-nano` or `gpt-4o-mini` also work.
3. Select **Deploy** → **Default settings** (or **Custom settings** to change the name or capacity). The deployment
   name defaults to the model name; keep it simple, e.g. `gpt-4.1-mini`. Select **Deploy**.
4. Check the deployment shows **Succeeded** (**Build** → **Models**). Azure OpenAI models sold by Azure need no
   Marketplace agreement. If you get a quota or region error, try another region or lower the tokens-per-minute.

## 3. Copy the endpoint and key

The project **Home** page shows the project endpoint and API key; a deployment's detail page (**Build** → **Models**)
also shows endpoint details and keys.

The app calls the **OpenAI v1 API** with the official `openai` Python SDK: `OpenAI(base_url="https://<resource>.openai.azure.com/openai/v1/", api_key=...)`.
No `api-version` is needed. Both `https://<resource>.openai.azure.com` and `https://<resource>.services.ai.azure.com`
hosts are accepted. Paste whichever endpoint the portal shows: the app keeps only the host and appends `/openai/v1/`.

## 4. Configure InsideMatch

Create `.env` in the repo root (it is git-ignored; never commit it or paste the key anywhere public):

```
AI_PROVIDER=foundry
FOUNDRY_ENDPOINT=https://<your-resource>.openai.azure.com
FOUNDRY_API_KEY=<key from the portal>
FOUNDRY_MODEL_DEPLOYMENT=gpt-4.1-mini
```

Then restart `make dev`. `/health` reports `"ai_provider": "foundry"` and the UI badge shows **AI: Foundry**.

## 5. Keyless auth on Azure (managed identity)

In Azure Container Apps the API uses its managed identity instead of a key: set `FOUNDRY_USE_MANAGED_IDENTITY=true`
and leave `FOUNDRY_API_KEY` empty. The identity needs the **Cognitive Services OpenAI User** role on the Foundry
resource. The app uses `DefaultAzureCredential` with the token scope `https://ai.azure.com/.default`. The Bicep in
`infrastructure/` assigns the role (Step 15).

## 6. Prewarm before a demo

`make prewarm` runs every demo_01 trigger against Foundry ahead of the demo/video, so judges never wait on a model,
and prints the validator result for each (Step 10).
