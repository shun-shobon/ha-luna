# Luna

Home Assistant Integration「Luna」は、自作のパーソナルエージェント[Luna](https://github.com/shun-shobon/luna-chat)をHome AssistantのAssistで会話エージェントとして選べるようにするCustom Integrationです。

[English](#english)

## 動作

Assistに話しかけた内容を、LunaのHTTP API（`POST {LunaのURL}/home-assistant/conversation`）へそのまま送り、Lunaの返答をAssistの応答として返します。返答の生成や会話履歴の管理はLuna側が行い、このIntegrationは中継だけを担います。

- 送信する情報: 発話テキスト、言語、会話ID、発話したデバイスとAssist satelliteのID、デバイス名（ユーザーが付けた名前を優先）、デバイスのエリア名、Home Assistantのユーザー名。解決できない項目は`null`で送ります。
- Lunaが何も言わないことを選んだ場合は、読み上げずに終わります。
- Lunaが続けて聞き取ることを求めた場合は、対応するVoice satelliteが続けて聞き取ります。
- Lunaの返答には数十秒かかることがあるため、待ち時間の上限はAssistパイプライン全体の既定値と同じ300秒にしています。
- タイムアウト、接続失敗、Lunaの停止処理中、Lunaの実行失敗、不正な応答のときは、短いエラー文（英語）をAssistの応答として返し、Home Assistantのログに記録します。

## Luna側で必要な設定

Home AssistantからLunaのHTTP APIへ届くように、Lunaの待ち受けアドレスをLANへ公開してください。Native起動では`LUNA_HTTP_HOST=0.0.0.0`を設定します。Docker Composeで動かす場合は、ホスト側のポートがループバックにだけ公開されていないことも確認してください。

LunaのHTTP APIには認証がありません。同じネットワークに入れる人や機器は誰でもLunaへ話しかけられるため、信頼できるLANの中だけで使ってください。

## インストール

Home Assistant 2026.10以降が必要です。

### HACS

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=shun-shobon&repository=ha-luna&category=integration)

1. 上のボタンを開くか、HACSのCustom repositoriesへ `https://github.com/shun-shobon/ha-luna` をIntegrationとして追加します。
2. HACSから「Luna」をインストールします。
3. Home Assistantを再起動します。
4. 「設定」、「デバイスとサービス」、「統合を追加」、「Luna」の順に開き、LunaのURL（例: `http://192.168.0.103:3000`）を入力します。

追加できるLunaは1つだけです。設定時にLunaへの接続確認は行いません。

## Assistで使う

1. 「設定」、「音声アシスタント」を開き、使うアシスタントを編集するか新しく追加します。
2. 「会話エージェント」で「Luna」を選んで保存します。

Voice satelliteなどのデバイスでは、そのデバイスに割り当てたアシスタントでLunaが使われます。

## Development

Python 3.14.2以上3.15未満と[uv](https://docs.astral.sh/uv/)を使用します。

```shell
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

テストはLunaのHTTP APIをモックし、実際のLunaへはアクセスしません。

## License

[MIT License](LICENSE)

## English

The Luna Home Assistant custom integration makes [Luna](https://github.com/shun-shobon/luna-chat), a personal agent, selectable as a conversation agent in Assist. It forwards each utterance to `POST {Luna URL}/home-assistant/conversation` with the language, conversation ID, device and satellite IDs, and the device, area, and user names, then returns Luna's reply as the Assist response. Luna owns reply generation and conversation history.

Luna's HTTP API must listen on the LAN (`LUNA_HTTP_HOST=0.0.0.0`). The API has no authentication, so use it only on a trusted network.

Home Assistant 2026.10 or later is required. Add `https://github.com/shun-shobon/ha-luna` to HACS as a custom Integration repository, install Luna, restart Home Assistant, and add Luna from Settings, Devices & services with Luna's URL. Then select Luna as the conversation agent of an assistant in Settings, Voice assistants.
