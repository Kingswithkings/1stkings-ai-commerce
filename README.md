# 1stkings AI Commerce

This app now supports two ordering channels that share the same cart and checkout logic:

- Web chat at `/store/[slug]`
- WhatsApp conversational ordering through the backend webhook

## Backend WhatsApp setup

The WhatsApp channel can run through either Meta Cloud API or SendPulse.

Set these environment variables before running the FastAPI app in production:

```bash
# App config
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=sqlite:///./store.db
CORS_ORIGINS=http://localhost:3000,https://1stkings-ai-commerce.vercel.app

# Meta Cloud API
WHATSAPP_ACCESS_TOKEN=your_meta_cloud_api_token
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_API_VERSION=v22.0

# SendPulse
SENDPULSE_API_ID=your_sendpulse_api_id
SENDPULSE_API_SECRET=your_sendpulse_api_secret
```

Each store can also be configured in the `stores` table with:

- `whatsapp_enabled`
- `whatsapp_provider` (`meta` or `sendpulse`)
- `whatsapp_number`
- `whatsapp_phone_number_id`
- `whatsapp_bot_id`
- `whatsapp_verify_token`

## WhatsApp webhook endpoints

- Verify webhook: `GET /channels/whatsapp/webhook`
- Receive and process WhatsApp messages: `POST /channels/whatsapp/webhook`

`GET /channels/whatsapp/webhook` is used for Meta verification. SendPulse uses the same `POST /channels/whatsapp/webhook` endpoint for incoming messages.

The webhook uses the same order engine as `/chat`, so customers can:

- add items
- remove items
- view cart
- checkout
- confirm or cancel orders
