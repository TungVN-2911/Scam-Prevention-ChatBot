# Kịch bản thuyết trình — Scam-Prevention-ChatBot

> Kịch bản để nói miệng, không phải tài liệu kỹ thuật. Viết theo ngôi "em", dựa trên implementation thực tế trong code tại thời điểm 2026-08-27.

---

## 1. Giới thiệu tổng quan

Sản phẩm em xây dựng là **"Trợ lý cá nhân phòng, chống lừa đảo trực tuyến"**.

Đây là một chatbot tiếng Việt, giúp người dùng:

- tìm hiểu các hình thức lừa đảo phổ biến hiện nay,
- nhận biết dấu hiệu đáng ngờ trong một tình huống cụ thể,
- biết cách phòng tránh trước khi sự việc xảy ra,
- biết nên làm gì nếu đã lỡ gặp sự cố,
- tìm kênh hỗ trợ, hotline chính thức,
- và luyện tập khả năng nhận diện lừa đảo thông qua các mini-game.

Nói ngắn gọn: đây không phải một chatbot hỏi-đáp chung chung, mà là một trợ lý tập trung vào một vấn đề cụ thể, gắn với đời sống thật của người dùng Việt Nam.

## 2. Vấn đề và mục tiêu

Vấn đề em muốn giải quyết là: thông tin về lừa đảo trực tuyến hiện nay nằm rải rác ở rất nhiều nguồn — báo chí, mạng xã hội, cảnh báo của ngân hàng, thông báo của cơ quan công an... Người dùng bình thường khó biết chính xác:

- tình huống họ đang gặp có phải là một chiêu lừa đảo hay không,
- dấu hiệu nào là đáng ngờ,
- nên xử lý ra sao,
- và thông tin nào thực sự đáng tin cậy.

Mục tiêu của em là tạo ra **một điểm tương tác bằng ngôn ngữ tự nhiên**: người dùng chỉ cần mô tả tình huống của mình bằng tiếng Việt, và nhận lại câu trả lời có căn cứ, dựa trên một knowledge base em đã chuẩn bị sẵn.

Điều em muốn nhấn mạnh ngay từ đầu: đây **không phải** một chatbot chỉ dựa vào kiến thức nội tại mà Gemini đã học sẵn. Em chủ động cho hệ thống tra cứu dữ liệu đã chuẩn bị trước, rồi mới để Gemini dùng dữ liệu đó để trả lời — vì trong một lĩnh vực nhạy cảm như lừa đảo, một câu trả lời sai về hotline, quy định pháp luật, hay cách xử lý có thể gây hại thật cho người dùng.

*(Chuyển tiếp)* Để hiểu rõ hơn tại sao em làm vậy, em sẽ đi qua workflow tổng thể của hệ thống.

## 3. Workflow tổng thể

Về tổng thể, một yêu cầu đi qua các lớp sau:

```
Người dùng
  → Streamlit (frontend)
  → FastAPI (backend)
  → Xác định intent (rule-based)
  → rẽ nhánh theo intent
```

Ở đây có một điểm quan trọng em muốn nói rõ: **không phải mọi câu hỏi đều đi qua toàn bộ pipeline RAG**. Hệ thống rẽ nhánh ngay sau bước xác định intent:

- Nếu intent là **tra hotline** (`hotline_lookup`) — ví dụ người dùng hỏi "số điện thoại báo lừa đảo" — hệ thống trả lời trực tiếp từ một file dữ liệu tĩnh (`data/hotlines.json`), **không gọi Gemini, không qua Pinecone**. Lý do đơn giản: đây là thông tin cố định, không cần AI can thiệp, và tránh rủi ro AI tự bịa số điện thoại.
- Với **10 intent còn lại** (dấu hiệu lừa đảo, cách phòng tránh, xử lý sau khi bị lừa, quy định pháp luật, câu hỏi chung...), hệ thống mới thực sự đi qua luồng RAG: suy ra category từ intent → tìm kiếm vector trên Pinecone → ghép context → gọi Gemini.
- Với 3 intent liên quan trực tiếp đến việc *đánh giá một tình huống cụ thể* (`scam_identification`, `scam_pattern_search`, `victim_help`), em có thêm **một bước kiểm tra phụ**: gọi Gemini lần thứ hai chỉ để hỏi "tình huống này có khớp với một hình thức lừa đảo đã biết trong dữ liệu hay không". Em sẽ giải thích kỹ hơn ở phần Chat.

Việc xác định intent hiện tại là **rule-based**: em chuẩn hoá câu hỏi (bỏ dấu, viết thường), rồi kiểm tra xem nó có chứa một trong các cụm từ mẫu đã định nghĩa sẵn cho 11 intent hay không (ví dụ "dấu hiệu lừa đảo", "tôi vừa bị lừa", "lừa đảo tuyển dụng"...). Nếu không khớp cụm nào, mặc định rơi vào `general_question`.

*(Chuyển tiếp)* Bây giờ em sẽ đi sâu vào phần quan trọng nhất: chức năng Chat, vì đây là nơi tập trung phần lớn kỹ thuật của sản phẩm.

## 4. Đi sâu vào chức năng Chat

Em sẽ minh hoạ bằng một ví dụ thật. Giả sử người dùng nhập:

> "em vừa nhận được cuộc gọi tự xưng là nhân viên ngân hàng, họ nói tài khoản của em có giao dịch bất thường và yêu cầu em đọc mã OTP. em nên làm gì?"

Hệ thống xử lý câu này như sau:

1. Frontend gửi câu hỏi (kèm lịch sử hội thoại gần đây) tới endpoint `/api/chat` của FastAPI.
2. Backend xác định intent — câu này rơi vào `victim_help` (người dùng có khả năng đã/đang bị nhắm tới, cần hướng dẫn xử lý ngay).
3. Vì `victim_help` là 1 trong 3 intent "nhạy cảm" em nói ở trên, hệ thống làm 2 việc song song về mặt logic:
   - Truy vấn Pinecone với category `recovery` để lấy context cho câu trả lời chính (làm gì khi gặp tình huống này).
   - Truy vấn thêm một lần nữa với category `scams` (top 3 kết quả) chỉ để phục vụ bước kiểm tra "tình huống này có khớp hình thức lừa đảo nào đã biết không".
4. Với kết quả truy vấn `scams`, em gọi Gemini một lần, với một prompt buộc trả lời đúng 1 từ: `KHOP` hoặc `CHUA_BIET`. Nếu Gemini trả lời `CHUA_BIET`, hệ thống tự động ghi lại tình huống này vào `data/pending_reports.json` để em review thủ công sau, đồng thời chèn thêm một ghi chú vào prompt chính để Gemini biết là "tình huống này chưa từng được ghi nhận, đừng khẳng định chắc chắn nó là hình thức lừa đảo đã biết".
5. Prompt cuối cùng được ghép từ: system prompt cố định + tối đa 6 lượt hội thoại gần nhất + context lấy được từ Pinecone + câu hỏi hiện tại — gửi 1 lần cho Gemini để sinh câu trả lời.
6. Câu trả lời cùng danh sách nguồn (`sources`) được trả về frontend, và được lưu vào SQL Server nếu cuộc trò chuyện đã có session.

Bước 3–4 chính là cơ chế em dùng để giảm rủi ro Gemini "vơ đũa cả nắm" — tự tin gán một tình huống mới, chưa từng gặp, vào một hình thức lừa đảo đã biết chỉ vì nó nghe có vẻ giống.

*(Chuyển tiếp)* Đến đây em đã nói rõ chatbot hoạt động thế nào. Câu hỏi quan trọng hơn tiếp theo là: những thông tin mà chatbot dùng để trả lời thực sự đến từ đâu?

## 5. Data được chuẩn bị như thế nào

Knowledge base của em được tổ chức thành 4 nhóm, nằm trong thư mục `knowledge_base/sources/`:

```
sources/
├── scams/          — các hình thức và kịch bản lừa đảo cụ thể (1 file JSON)
├── prevention/      — dấu hiệu nhận biết và cách phòng tránh (file Markdown)
├── recovery/        — hướng xử lý khi đã gặp sự cố (file Markdown)
└── regulations/      — quy định, căn cứ pháp lý liên quan (file Markdown)
```

`prevention/`, `recovery/`, `regulations/` là các file `.md` viết tay theo từng chủ đề (ví dụ `otp_security.md`, `bank_transfer_recovery.md`, `cybersecurity_law.md`...). `scams/scams.json` là một file JSON, mỗi phần tử mô tả một hình thức lừa đảo với các trường: tên, category, kịch bản, dấu hiệu cảnh báo, cách phòng ngừa, và hướng xử lý nếu đã là nạn nhân — kèm nguồn tham khảo cụ thể (tên tổ chức, tiêu đề bài viết, URL).

Quy trình chuẩn bị dữ liệu em làm là:

```
Chọn nguồn thông tin đáng tin cậy
  → đọc và kiểm tra nội dung
  → trích xuất thông tin quan trọng
  → viết lại/chuẩn hoá bằng tiếng Việt, phân theo 4 nhóm ở trên
  → lưu thành file trong knowledge_base
  → (bước ingest) chunk → embedding → upsert vào Pinecone
```

Em ưu tiên các nguồn chính thống — báo chí uy tín, cơ quan nhà nước — và ghi rõ nguồn ngay trong dữ liệu, để khi chatbot trích dẫn, thông tin đó có thể truy ngược lại được, không phải do AI tự nghĩ ra.

*(Chuyển tiếp)* Có dữ liệu rồi, bước tiếp theo là biến nó thành dạng mà hệ thống tìm kiếm được — đó là chunking.

## 6. Chunking

Chunking là bước chia nhỏ tài liệu thành các đoạn (chunk) trước khi đưa vào embedding. Em không embed nguyên một file dài thành 1 vector duy nhất, vì như vậy khi tìm kiếm, hệ thống sẽ trả về cả một tài liệu dài, lẫn lộn nhiều ý, thay vì đúng đoạn liên quan tới câu hỏi.

Cách em làm cụ thể (trong `backend/app/rag_engine/chunking.py`), với 2 loại dữ liệu khác nhau:

- **Với file Markdown** (`prevention/`, `recovery/`, `regulations/`): em chia theo **heading** (dòng bắt đầu bằng `#`) — đây là **structural chunking dựa trên cấu trúc Markdown**, không phải semantic chunking bằng AI. Sau khi tách theo heading, em gộp các đoạn liền kề lại với nhau cho đến khi đạt giới hạn khoảng 1000 ký tự, để tránh chunk quá ngắn hoặc quá dài. Hiện tại **không có overlap** giữa các chunk.
- **Với dữ liệu `scams.json`**: mỗi hình thức lừa đảo được gộp thành **đúng 1 chunk** — ghép tên, category, kịch bản, dấu hiệu cảnh báo, cách phòng ngừa, hướng xử lý thành 1 đoạn văn bản hoàn chỉnh theo template cố định, không chia nhỏ thêm. Lý do là mỗi bản ghi lừa đảo là một đơn vị thông tin trọn vẹn, tách nhỏ ra sẽ làm mất ngữ cảnh (ví dụ tách "dấu hiệu cảnh báo" khỏi "tên hình thức lừa đảo" thì chunk đó vô nghĩa khi đứng riêng).

Mỗi chunk được gắn metadata gồm `category` (scams/prevention/recovery/regulations) và `source` (đường dẫn file gốc) — đây chính là thứ em dùng để lọc kết quả tìm kiếm theo category ở bước retrieval.

*(Chuyển tiếp)* Có chunk rồi, bước kế tiếp là biến từng chunk thành vector — đây là embedding.

## 7. Embedding

Embedding là quá trình biến một đoạn văn bản thành một vector số — để máy tính có thể so sánh "mức độ giống nhau về ngữ nghĩa" giữa hai đoạn văn bản bằng phép toán, thay vì so khớp từ khoá.

Em cần bước này vì **tìm kiếm theo từ khoá (keyword search) có giới hạn rõ rệt**: nếu người dùng hỏi "họ gọi điện xưng là công an" nhưng tài liệu viết là "đối tượng giả danh cơ quan chức năng", tìm theo từ khoá đơn thuần sẽ không khớp — trong khi hai câu này về mặt ngữ nghĩa là rất gần nhau. Semantic search giải quyết đúng vấn đề này, và với câu hỏi tiếng Việt tự nhiên (nhiều cách diễn đạt cho cùng một ý), đây gần như là điều bắt buộc.

Về implementation (`backend/app/rag_engine/embedding.py`): em dùng **Ollama chạy local**, gọi qua endpoint `/api/embed`, với model mặc định là `nomic-embed-text` (cấu hình được qua biến môi trường `OLLAMA_EMBED_MODEL`). Đây không phải Gemini embedding.

Lý do em chọn Ollama thay vì embedding API của Gemini: embedding là bước phải chạy **rất nhiều lần** — mỗi chunk lúc ingest, và mỗi câu hỏi lúc người dùng chat. Gemini free tier chỉ cho 20 request/ngày; nếu dùng Gemini để embedding, em sẽ tốn quota cho việc tìm kiếm thay vì để dành cho việc sinh câu trả lời. Chạy embedding local bằng Ollama giúp tách hẳn khối lượng công việc này ra khỏi quota Gemini, đổi lại là em phải tự chạy Ollama, và chất lượng embedding trên corpus nhỏ (23 hình thức lừa đảo) của em chưa được hiệu chỉnh kỹ — đây là một giới hạn em thừa nhận trong README, không phải điểm mạnh.

*(Chuyển tiếp)* Có vector rồi, em cần một nơi để lưu và tìm kiếm chúng — đó là vector database.

## 8. Vector Database / Pinecone

Tại sao cần vector database mà không lưu thẳng vào JSON hay SQL Server: vì tìm kiếm theo vector đòi hỏi tính toán khoảng cách/độ tương đồng (similarity) giữa vector câu hỏi và hàng nghìn vector đã lưu — việc này cần cấu trúc index chuyên biệt (ví dụ approximate nearest neighbor) để nhanh, thứ mà JSON hay các câu `SELECT` thông thường của SQL không làm được hiệu quả.

Em chọn **Pinecone** vì đây là dịch vụ managed — em không cần tự cài đặt, vận hành hay scale một vector database, chỉ cần gọi API. Với quy mô dữ liệu của em (vài chục file), việc tự host một vector DB (Qdrant, Chroma...) sẽ tốn công vận hành không tương xứng với lợi ích.

Về cách em dùng cụ thể (`backend/app/rag_engine/retrieval.py`):

- Khi **upsert** (lúc chạy `ingest.py`): với mỗi chunk, em embed rồi lưu vào Pinecone dưới dạng `{id, vector, metadata}` — trong đó **metadata chứa cả `category`, `source`, và toàn bộ text gốc của chunk**. Em lưu luôn text vào metadata để khi truy vấn, kết quả trả về đã có sẵn nội dung, không cần round-trip thêm lần nào để lấy lại văn bản gốc.
- Khi **query**: em embed câu hỏi, gọi Pinecone với `top_k=5` cho câu trả lời chính (`top_k=3` riêng cho bước kiểm tra phụ ở mục 4), và nếu intent map được sang một category cụ thể, em thêm filter `{"category": {"$eq": category}}` để chỉ tìm trong đúng nhóm dữ liệu liên quan — ví dụ câu hỏi về pháp luật sẽ chỉ tìm trong `regulations`, không lẫn với `prevention`.
- Em hiện **không dùng namespace** — toàn bộ dữ liệu nằm trong 1 index duy nhất, phân biệt bằng metadata `category`.

*(Chuyển tiếp)* Có được các chunk liên quan rồi, bước cuối cùng là dùng chúng để tạo ra câu trả lời — đây chính là RAG kết hợp với Gemini.

## 9. Retrieval + RAG + Gemini

RAG là viết tắt của Retrieval-Augmented Generation. Nói theo cách dễ hiểu: **thay vì để Gemini tự trả lời hoàn toàn dựa trên kiến thức nó đã học sẵn, em cho hệ thống đi tìm những thông tin liên quan trong knowledge base của em trước, rồi mới đưa những thông tin đó cho Gemini để nó tổng hợp thành câu trả lời.**

Luồng cụ thể:

```
Câu hỏi của người dùng
  → Retrieval: tìm chunk liên quan trong Pinecone (đã nói ở mục 8)
  → Context: ghép các chunk tìm được thành 1 đoạn văn bản
  → Gemini: đọc context + câu hỏi + lịch sử hội thoại, sinh câu trả lời
  → Câu trả lời có căn cứ (grounded) từ dữ liệu thật
```

Vai trò của từng thành phần rất rõ ràng: **Pinecone không tự tạo ra câu trả lời** — nó chỉ có nhiệm vụ tìm đúng ngữ cảnh liên quan. **Gemini không phải là nguồn dữ liệu chính** — vai trò của nó là đọc hiểu ngữ cảnh đã tìm được, kết hợp với câu hỏi, rồi diễn đạt lại thành một câu trả lời tự nhiên bằng tiếng Việt.

Gemini trong dự án của em (`backend/app/llm_gateway/gemini_gateway.py`) được dùng ở **2 chỗ**:

1. **Sinh câu trả lời chính** cho người dùng — model em dùng là `gemini-3.6-flash`, gọi qua `google-genai` SDK.
2. **Kiểm tra phụ** ("tình huống này có khớp hình thức lừa đảo đã biết không") — đã nói ở mục 4, cũng dùng cùng model, chỉ khác prompt.

Em **không** dùng cơ chế function-calling/tool-calling thật sự của Gemini API — mặc dù system prompt của em có một mục hướng dẫn về "sử dụng tool", đó chỉ là hướng dẫn hành vi bằng văn bản, còn việc lấy dữ liệu (như tra hotline) trong code thực tế được xử lý trực tiếp bằng logic Python trước khi gọi Gemini, không phải Gemini tự quyết định gọi tool.

Về việc **bám vào nguồn**, em làm bằng 2 lớp:

- **Lớp 1 — system prompt**: em viết một system prompt khá dài và chi tiết, với các nguyên tắc rõ ràng như "nếu không biết thì không được bịa", "không tự tạo hotline/điều luật/số liệu", "nếu context không đủ, phải nói rõ giới hạn", và một danh sách tự-kiểm-tra Gemini phải làm trước khi trả lời (có bịa thông tin không, có dùng đúng dữ liệu từ RAG không...).
- **Lớp 2 — cơ chế kiểm tra tình huống lạ**: như đã nói ở mục 4, nếu Gemini xác nhận một tình huống không khớp dữ liệu đã biết, hệ thống chủ động thêm cảnh báo vào prompt, đồng thời ghi log lại để em review — thay vì để Gemini tự tin đưa ra kết luận sai.

Đây là 2 lớp phòng thủ bổ sung cho nhau: system prompt là hướng dẫn hành vi chung, còn cơ chế kiểm tra là một bước xử lý bằng code, không phụ thuộc hoàn toàn vào việc Gemini có "nghe lời" prompt hay không.

*(Chuyển tiếp)* Em vừa giải thích xong toàn bộ kỹ thuật đứng sau chức năng Chat. Trước khi sang các chức năng phụ, em muốn tổng hợp lại lý do em chọn từng công nghệ.

## 10. Vì sao em chọn các công nghệ/phương pháp này

| Công nghệ | Vấn đề cần giải quyết | Vì sao chọn | Đánh đổi |
|---|---|---|---|
| **FastAPI** | Cần 1 backend API nhẹ, tách biệt với frontend | Phù hợp ứng dụng AI viết bằng Python, có validation qua Pydantic sẵn | Không có gì đáng kể ở quy mô này |
| **Streamlit** | Cần UI nhanh để phát triển, không muốn viết frontend riêng biệt | Viết UI bằng Python thuần, tốc độ phát triển nhanh, phù hợp project cá nhân | Khó tuỳ biến UI phức tạp/production-grade |
| **Google Gemini** (`gemini-3.6-flash`) | Cần LLM để hiểu ngôn ngữ tự nhiên tiếng Việt và sinh câu trả lời | Chất lượng tốt cho tiếng Việt, đã tích hợp qua SDK chính thức | Free tier giới hạn 20 request/ngày — buộc em phải tiết kiệm quota ở mọi chỗ khác (intent, embedding) |
| **Ollama + `nomic-embed-text`** | Cần embedding cho semantic search, chạy rất nhiều lần | Miễn phí, chạy local, không đụng tới quota Gemini | Phải tự chạy Ollama; chất lượng embedding trên corpus nhỏ chưa được hiệu chỉnh tốt |
| **Pinecone** | Cần lưu và tìm kiếm vector hiệu quả | Managed service, không cần tự vận hành hạ tầng vector DB | Phụ thuộc dịch vụ bên thứ ba, cần API key |
| **SQL Server (`pyodbc`)** | Cần lưu lịch sử chat, XP, lịch sử Quiz/Detective | Hạ tầng sẵn có; dùng `pyodbc` trực tiếp, tận dụng transaction thủ công (`autocommit=False`) cho các thao tác cần atomic mà không cần thêm ORM | Phải tự viết SQL thay vì dùng ORM |
| **pytest** | Cần đảm bảo logic (chấm điểm, lưu trữ, API) không bị gãy khi sửa code | Chuẩn phổ biến cho Python, tích hợp tốt với FastAPI TestClient | — |
| **Rule-based intent detection** | Cần phân loại ý định câu hỏi trước khi tìm kiếm | Nhanh, miễn phí, đủ chính xác cho tập intent cố định (11 intent + fallback) | Cứng nhắc — không nhận ra được cách diễn đạt lạ, khác hoàn toàn các mẫu đã viết |

### Vì sao em không dùng MCP

Có một điểm em muốn chủ động nói trước, phòng khi có người để ý thấy: trong `requirements.txt` có khai báo package `mcp`, nhưng em **không thực sự dùng MCP** trong sản phẩm này — đây là còn sót lại từ giai đoạn scaffold ban đầu, em chưa gỡ bỏ. Em muốn giải thích rõ vì sao, vì đây là một quyết định có chủ đích, không phải bỏ sót.

**MCP là gì, nói ngắn gọn**: Model Context Protocol là một giao thức chuẩn hoá cách một LLM client (ví dụ Claude, hoặc một agent nào đó) kết nối tới các "MCP server" cung cấp tool/resource, để LLM có thể tự quyết định lúc nào cần gọi tool nào, với tham số gì — mà không cần viết tích hợp riêng cho từng cặp client-server. Giá trị lớn nhất của nó nằm ở bài toán nhiều client × nhiều server: thay vì phải viết M×N tích hợp riêng lẻ, mỗi server chỉ cần implement chuẩn MCP một lần là mọi client hỗ trợ MCP đều dùng được.

**Vì sao mô hình đó không khớp với dự án của em, cụ thể theo 4 lý do:**

1. **Ngược triết lý deterministic**: Toàn bộ thiết kế của em đi theo hướng ngược lại với "để AI tự quyết định" — em cố tình xử lý các việc có thể xử lý bằng code thuần (tra hotline, chấm điểm Quiz/Detective, chọn Scam of the Day) bằng logic Python cố định, không giao cho AI quyết định khi nào cần gọi cái gì. Nếu dùng MCP, đúng bản chất của nó là để Gemini tự quyết định có cần gọi tool `get_hotlines` hay không — điều đó đi ngược lại chủ đích ban đầu của em là giảm tối đa các điểm mà AI có thể "tự quyết định sai".
2. **Chi phí quota không xứng đáng**: Gemini free tier chỉ có 20 request/ngày. Cơ chế function-calling của MCP cần Gemini "suy nghĩ" xem có cần gọi tool không trước khi trả lời — về bản chất là tốn thêm ít nhất 1 lượt gọi model cho bước quyết định đó, có thể còn thêm 1 lượt nữa sau khi có kết quả tool để tổng hợp câu trả lời cuối. Với cách em đang làm — quyết định "cần lấy dữ liệu gì" bằng rule-based intent detection, chạy hoàn toàn bằng code, không gọi AI — em tiết kiệm được toàn bộ chi phí đó.
3. **Tập tool quá nhỏ và cố định để cần chuẩn hoá**: MCP thực sự phát huy giá trị khi có nhiều tool, tool thay đổi thường xuyên, hoặc cần nhiều client khác nhau (Claude Desktop, một agent khác, một app khác...) cùng dùng chung 1 bộ tool. Ở đây em chỉ có 2 nguồn dữ liệu tĩnh (hotline, pattern lừa đảo) và duy nhất 1 client dùng chúng (chính backend của em) — viết thẳng bằng `scam_connector` (một Protocol + 1 class đọc JSON) đơn giản hơn nhiều so với dựng cả một MCP server (cần chạy như 1 process riêng, giao tiếp qua stdio hoặc HTTP/SSE) chỉ để phục vụ đúng 1 client.
4. **Tăng độ phức tạp vận hành không cần thiết**: Có thêm 1 MCP server nghĩa là có thêm 1 process cần khởi động, theo dõi, và xử lý lỗi khi nó chết — trong khi hiện tại toàn bộ hệ thống của em chỉ cần chạy FastAPI backend và Streamlit frontend. Ở quy mô một sản phẩm cá nhân, thêm một lớp hạ tầng chỉ để "làm đúng chuẩn" mà không giải quyết vấn đề thực tế nào là không đáng.

Em không loại trừ khả năng dùng MCP sau này — nếu sản phẩm phát triển tới mức cần tích hợp nhiều nguồn dữ liệu bên ngoài thực sự (ví dụ tra cứu số điện thoại lừa đảo qua một API bên thứ ba, hay để nhiều agent khác nhau cùng dùng chung bộ tool này), lúc đó chi phí chuẩn hoá của MCP mới bắt đầu xứng đáng với lợi ích nó mang lại.

### Câu hỏi thường gặp: chạy Ollama local và gọi API Pinecone thì có bất lợi gì

Kiến trúc RAG của em có 2 nửa khác tính chất: Ollama chạy **local** ngay trên máy chạy backend, còn Pinecone là dịch vụ **gọi qua API** ra ngoài. Mỗi nửa có đánh đổi riêng mà em muốn nói rõ, không chỉ kể ưu điểm:

**Chạy Ollama local:**
- Backend không còn "nhẹ" theo nghĩa chỉ là code thuần — máy chạy backend bắt buộc phải cài và chạy thêm Ollama như một service nền, cần đủ RAM/CPU để chạy model embedding. Nếu sau này em muốn deploy backend lên một nền tảng chỉ hỗ trợ chạy code (không cho chạy thêm service khác), em sẽ không "deploy code" đơn giản được nữa.
- Không tự động mở rộng (scale) khi lượng người dùng tăng — một dịch vụ managed thường tự scale, còn Ollama chạy trên 1 máy sẽ là điểm nghẽn nếu nhiều request embedding đến cùng lúc.
- Nếu Ollama trên máy đó ngừng chạy hoặc lỗi, toàn bộ luồng RAG — cả lúc ingest lẫn lúc chat — sẽ hỏng ngay, vì embedding là bước bắt buộc ở cả hai chiều, và đây là một điểm phụ thuộc nằm ngay trên máy của em, không có ai backup thay.

**Gọi API Pinecone:**
- Mỗi lần truy vấn đều phải đi ra mạng tới Pinecone, nên có thêm độ trễ mạng; nếu mất kết nối internet hoặc Pinecone gặp sự cố ở phía họ, tính năng tìm kiếm sẽ ngừng hoạt động — rủi ro này nằm ngoài tầm kiểm soát của em.
- Vì là managed service, em phụ thuộc vào chính sách giá và giới hạn (rate limit, dung lượng) của Pinecone — khi dữ liệu hoặc lượng truy vấn tăng, chi phí tăng theo, khác với tự host nơi chi phí chủ yếu là hạ tầng cố định.
- Cách em gọi Pinecone (cấu trúc filter, quản lý index) là đặc thù riêng của Pinecone — nếu sau này muốn đổi sang vector DB khác, em phải viết lại phần `retrieval.py`, không chuyển đổi được ngay lập tức.

Em chọn kết hợp theo cách này — local cho phần cần chạy rất nhiều lần và muốn miễn phí (embedding), managed cloud cho phần cần hạ tầng chuyên biệt mà em không muốn tự vận hành (vector search) — nhưng đây là một đánh đổi có 2 mặt, không phải lựa chọn hoàn toàn không có chi phí.

*(Chuyển tiếp)* Bây giờ em sẽ demo trực tiếp để mọi người thấy toàn bộ luồng này hoạt động trong thực tế.

## 11. Demo flow

"Đây là giao diện chính của sản phẩm."

"Ở phần Chat, người dùng có thể đặt câu hỏi bằng ngôn ngữ tự nhiên, giống như đang nhắn tin hỏi một người tư vấn thật."

*(Gõ vào ô chat)*

> "em vừa nhận được cuộc gọi tự xưng là nhân viên ngân hàng, họ nói tài khoản của em có giao dịch bất thường và yêu cầu em đọc mã OTP. em nên làm gì?"

*(Trong lúc chờ phản hồi, giải thích ngắn gọn — không đi sâu lại chi tiết đã nói ở mục 4 và 9)*

"Câu hỏi này được gửi tới backend, hệ thống xác định đây là tình huống người dùng có thể đang bị nhắm tới, nên tìm kiếm trong nhóm dữ liệu về cách xử lý sự cố. Đồng thời hệ thống cũng kiểm tra xem tình huống này có khớp với một hình thức lừa đảo đã biết hay không. Sau đó toàn bộ thông tin tìm được được đưa cho Gemini để tổng hợp thành câu trả lời cuối cùng."

*(Khi có kết quả)*

"Như các bạn thấy, câu trả lời có kèm hướng dẫn xử lý cụ thể, và ở dưới có nguồn dữ liệu mà câu trả lời này dựa vào."

*(Chuyển tiếp)* "Ngoài Chat, sản phẩm còn có 3 chức năng phụ, em sẽ giới thiệu nhanh."

## 12. Các chức năng phụ

### Quiz — Kiểm tra kiến thức chống lừa đảo

Người dùng chọn 1 trong 4 chủ đề (nhận diện lừa đảo, phòng tránh, khắc phục hậu quả, quy định pháp luật), làm 10 câu trắc nghiệm tĩnh. Chấm điểm hoàn toàn deterministic — dựa trên tỉ lệ đúng để xếp vào 1 trong 4 mức XP (100/75/50/20), **không qua AI**. Sau khi nộp bài, người dùng được xem lại từng câu sai kèm giải thích, và có thể mở lại lịch sử các lần làm bài trước đó.

### Scam of the Day

Mỗi ngày hiển thị 1 hình thức lừa đảo, chọn theo cách **deterministic dựa trên ngày** — cùng một ngày, mọi người xem thấy giống nhau (thuật toán: lấy số thứ tự ngày, chia lấy dư theo số lượng pattern hiện có; nếu pattern được chọn thiếu dữ liệu để hiển thị, tự động chuyển sang pattern kế tiếp). Mục tiêu là tạo thói quen học một chút kiến thức mỗi ngày, không cần chủ động tìm kiếm.

### Scam Detective

Đây là mini-game: người dùng đọc một tình huống lừa đảo có thật, rồi chọn ra các dấu hiệu đáng ngờ trong tình huống đó. Việc chấm điểm cũng **hoàn toàn deterministic** — đếm số dấu hiệu chọn đúng so với tổng số dấu hiệu cần tìm, quy ra phần trăm, rồi xếp vào cùng thang XP với Quiz. Sau khi nộp, hệ thống hiện đáp án đúng kèm giải thích cho từng dấu hiệu, và cũng lưu lại lịch sử để xem lại sau.

Em muốn nhấn mạnh: cả Quiz và Scam Detective **không dùng AI để chấm điểm** — đây là lựa chọn có chủ đích, vừa để đảm bảo kết quả công bằng, có thể kiểm chứng, vừa để không tốn thêm quota Gemini cho những việc không thực sự cần AI.

*(Chuyển tiếp)* Để kết thúc, em muốn tổng kết lại giá trị cốt lõi của sản phẩm.

## 13. Tổng kết

Em không chỉ xây dựng một chatbot hỏi-đáp đơn thuần, mà xây dựng một trợ lý cá nhân giúp người dùng đi qua đủ 5 bước: **hiểu** hình thức lừa đảo → **nhận diện** dấu hiệu → **phòng tránh** trước khi xảy ra → **xử lý** nếu đã gặp sự cố → và **luyện tập** để ghi nhớ lâu dài qua Quiz và Scam Detective.

Giá trị cốt lõi em muốn giữ xuyên suốt là cách tiếp cận RAG kết hợp knowledge base tự chuẩn bị: thông tin luôn có nguồn cụ thể, dễ cập nhật khi có hình thức lừa đảo mới, phù hợp sát với bối cảnh Việt Nam, và quan trọng nhất — giảm phụ thuộc vào kiến thức nội tại của LLM, vốn có thể lỗi thời hoặc không chính xác cho những thông tin cần độ tin cậy cao như hotline hay quy định pháp luật.

Đó là toàn bộ những gì em đã xây dựng. Cảm ơn mọi người đã lắng nghe.
