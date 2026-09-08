{
  "inputs": {
    "messages": [
      {
        "content": [
          {
            "text": "sebutkan chat awal saya apa",
            "type": "text"
          }
        ],
        "id": "01a0822a-7fa6-773f-9c57-c0bc1c4142a2",
        "type": "human"
      }
    ]
  },
  "outputs": {
    "last_result": {
      "displayed_count": 1,
      "formatted": "1. Rute: BTG ➔ SMG\n   - Tipe Truk: TRONTON BAK\n   - Ekspedisi: PT REMA LOGISTIK INDONESIA (WARESIX)\n   - Customer: WAVIN\n   - Rate: Rp 2.600.000\n   - DP: Rp 0\n   - Uang jalan: Rp 0",
      "has_more": false,
      "matched_step": "eksak",
      "message": "Ditemukan 1 data tarif yang cocok.",
      "needs_clarification": [],
      "options": {},
      "rates": [
        {
          "customer_id": 1319,
          "customer_nama": "WAVIN",
          "destinasi": "SMG",
          "destinasi_id": 3197,
          "dp": 0,
          "expedisi_id": 472,
          "expedisi_nama": "PT REMA LOGISTIK INDONESIA (WARESIX)",
          "id": 9074,
          "origin": "BTG",
          "rate": 2600000,
          "status": "published",
          "type_mobil": "TRONTON BAK",
          "type_mobil_id": 270,
          "uang_jalan": 0
        }
      ],
      "remaining_count": 0,
      "status": "success",
      "total_found": 1
    },
    "messages": [
      {
        "additional_kwargs": {},
        "content": [
          {
            "text": "berapa Harga rate ini=\nArmada : WB\nNopol : B 9613 UXS\nDriver : Rokib\nWA : 082387396596\nMuat : Grobokan ( PT.Pungkook )\nTujuan : Jakarta\n\nNotes :\n\nLaporan masuk dr Ex : WIDUS/F1",
            "type": "text"
          }
        ],
        "id": "01a08229-5a39-74d9-b31a-6d0e5cf13ff8",
        "response_metadata": {},
        "type": "human"
      },
      {
        "additional_kwargs": {
          "__gemini_function_call_thought_signatures__": {
            "call_183742": "El4KXAERTTIPZhEbK2dMzc2Ne2hOj1/TEHo2m+DtbD/hbjiXxXt6Ic3XA+dfECxGcRxv+C89eqzEr6UoW/NG2WDqszMDxYbPLn3AknCPXG0yRoQVYLacNuQmL9l/xL02"
          },
          "function_call": {
            "arguments": "{\"origin\": \"Grobokan ( PT.Pungkook )\", \"customer\": \"WIDUS/F1\", \"destinasi\": \"Jakarta\", \"type_mobil\": \"WB\"}",
            "name": "tools_rates"
          }
        },
        "content": [],
        "id": "lc_run--01a08229-5e07-7f71-833e-da7a7a109f97",
        "invalid_tool_calls": [],
        "response_metadata": {
          "finish_reason": "STOP",
          "model_name": "gemini-3.5-flash-lite",
          "model_provider": "google_genai",
          "safety_ratings": []
        },
        "tool_calls": [
          {
            "args": {
              "customer": "WIDUS/F1",
              "destinasi": "Jakarta",
              "origin": "Grobokan ( PT.Pungkook )",
              "type_mobil": "WB"
            },
            "id": "call_183742",
            "name": "tools_rates",
            "type": "tool_call"
          }
        ],
        "type": "ai",
        "usage_metadata": {
          "input_token_details": {
            "cache_read": 0
          },
          "input_tokens": 1119,
          "output_tokens": 52,
          "total_tokens": 1171
        }
      },
      {
        "additional_kwargs": {},
        "artifact": {
          "displayed_count": 2,
          "formatted": "1. Rute: PWD ➔ JKT\n   - Tipe Truk: WB\n   - Ekspedisi: PT WIDUS\n   - Customer: PUNGKOOK\n   - Rate: Rp 4.600.000\n   - DP: Rp 0\n   - Uang jalan: Rp 2.600.000\n\n2. Rute: PWD ➔ JKT\n   - Tipe Truk: WB\n   - Ekspedisi: PT F1 LOGIX\n   - Customer: PUNGKOOK\n   - Rate: Rp 4.200.000\n   - DP: Rp 0\n   - Uang jalan: Rp 2.600.000",
          "has_more": false,
          "matched_step": "tanpa_origin",
          "message": "Ditemukan 2 data tarif yang cocok.",
          "needs_clarification": [],
          "options": {},
          "rates": [
            {
              "customer_id": 45,
              "customer_nama": "PUNGKOOK",
              "destinasi": "JKT",
              "destinasi_id": 24,
              "dp": 0,
              "expedisi_id": 247,
              "expedisi_nama": "PT WIDUS",
              "id": 8095,
              "origin": "PWD",
              "rate": 4600000,
              "status": "published",
              "type_mobil": "WB",
              "type_mobil_id": 27,
              "uang_jalan": 2600000
            },
            {
              "customer_id": 45,
              "customer_nama": "PUNGKOOK",
              "destinasi": "JKT",
              "destinasi_id": 24,
              "dp": 0,
              "expedisi_id": 177,
              "expedisi_nama": "PT F1 LOGIX",
              "id": 3509,
              "origin": "PWD",
              "rate": 4200000,
              "status": "draft",
              "type_mobil": "WB",
              "type_mobil_id": 27,
              "uang_jalan": 2600000
            }
          ],
          "remaining_count": 0,
          "resolved": {
            "destinasi": [
              "JKT"
            ],
            "mitra": [
              "PT WIDUS",
              "PT F1 LOGIX"
            ],
            "origin": [
              "GRB"
            ],
            "type_mobil": [
              "WB"
            ]
          },
          "status": "success",
          "total_found": 2
        },
        "content": "{\"status\": \"success\", \"message\": \"Ditemukan 2 data tarif yang cocok.\", \"formatted\": \"1. Rute: PWD ➔ JKT\\n   - Tipe Truk: WB\\n   - Ekspedisi: PT WIDUS\\n   - Customer: PUNGKOOK\\n   - Rate: Rp 4.600.000\\n   - DP: Rp 0\\n   - Uang jalan: Rp 2.600.000\\n\\n2. Rute: PWD ➔ JKT\\n   - Tipe Truk: WB\\n   - Ekspedisi: PT F1 LOGIX\\n   - Customer: PUNGKOOK\\n   - Rate: Rp 4.200.000\\n   - DP: Rp 0\\n   - Uang jalan: Rp 2.600.000\", \"has_more\": false, \"needs_clarification\": [], \"options\": {}}",
        "id": "d113c2ca-4d6c-45a3-b6d8-94d044292f72",
        "name": "tools_rates",
        "response_metadata": {},
        "status": "success",
        "tool_call_id": "call_183742",
        "type": "tool"
      },
      {
        "additional_kwargs": {},
        "content": [
          {
            "extras": {
              "signature": "El4KXAERTTIPBYmlfhIH6Oumszig9O9QxCmVYR8Xstun4RlC5me83MRjrUrWOI4Ai0o7XQ8Ein3dnZ07LjQDo73LhIz/MkvubkL8vspwnoVTpVdcYiqNneKg8Ql5ERsv"
            },
            "index": 0,
            "text": "Halo! Berikut adalah rincian rate untuk pengiriman dari Grobogan (PT Pungkook) tujuan Jakarta dengan armada Wingbox (WB) sesuai laporan dari ekspedisi WIDUS dan F1 Logix:\n\n1. Rute: PWD ➔ JKT\n   - Tipe Truk: WB\n   - Ekspedisi: PT WIDUS\n   - Customer: PUNGKOOK\n   - Rate: Rp 4.600.000\n   - DP: Rp 0\n   - Uang jalan: Rp 2.600.000\n\n2. Rute: PWD ➔ JKT\n   - Tipe Truk: WB\n   - Ekspedisi: PT F1 LOGIX\n   - Customer: PUNGKOOK\n   - Rate: Rp 4.200.000\n   - DP: Rp 0\n   - Uang jalan: Rp 2.600.000\n\nAda hal lain atau rute lain yang perlu saya bantu cek?",
            "type": "text"
          }
        ],
        "id": "lc_run--01a08229-628f-7aa2-84f4-72317f5ad71e",
        "invalid_tool_calls": [],
        "response_metadata": {
          "finish_reason": "STOP",
          "model_name": "gemini-3.5-flash-lite",
          "model_provider": "google_genai",
          "safety_ratings": []
        },
        "tool_calls": [],
        "type": "ai",
        "usage_metadata": {
          "input_token_details": {
            "cache_read": 0
          },
          "input_tokens": 1503,
          "output_tokens": 226,
          "total_tokens": 1729
        }
      },
      {
        "additional_kwargs": {},
        "content": [
          {
            "text": "berapa Harga rate ini\nArmada : TRONTON\nNopol : BE 8948 ACU\nDriver  : Heri Subagiya Wibowo\nWA : +62 895-3134-0827\nAsal Muat : Batang ( PT.Wavin )\nTujuan : Jakarta ( Marunda )\n\nNotes :\n\nLaporan muat dari LOGWIN",
            "type": "text"
          }
        ],
        "id": "01a08229-f25e-76bb-8f03-776a2995205f",
        "response_metadata": {},
        "type": "human"
      },
      {
        "additional_kwargs": {
          "__gemini_function_call_thought_signatures__": {
            "call_163859": "El4KXAERTTIPyRiaiUQDs5X8siKjoODUP/2JBaCjbf9nMK539TDHPr4SW08cuKe7sN6Sixg25L96PxOL+VkPL39XJdqnnobY7zShxXAbTHM/KqhIrnbuYpn2p9CY8Oqu"
          },
          "function_call": {
            "arguments": "{\"type_mobil\": \"TRONTON\", \"origin\": \"Batang ( PT.Wavin )\", \"customer\": \"LOGWIN\", \"destinasi\": \"Jakarta ( Marunda )\"}",
            "name": "tools_rates"
          }
        },
        "content": [],
        "id": "lc_run--01a08229-f651-7b90-b280-ea19b2881919",
        "invalid_tool_calls": [],
        "response_metadata": {
          "finish_reason": "STOP",
          "model_name": "gemini-3.5-flash-lite",
          "model_provider": "google_genai",
          "safety_ratings": []
        },
        "tool_calls": [
          {
            "args": {
              "customer": "LOGWIN",
              "destinasi": "Jakarta ( Marunda )",
              "origin": "Batang ( PT.Wavin )",
              "type_mobil": "TRONTON"
            },
            "id": "call_163859",
            "name": "tools_rates",
            "type": "tool_call"
          }
        ],
        "type": "ai",
        "usage_metadata": {
          "input_token_details": {
            "cache_read": 0
          },
          "input_tokens": 1820,
          "output_tokens": 52,
          "total_tokens": 1872
        }
      },
      {
        "additional_kwargs": {},
        "artifact": {
          "displayed_count": 3,
          "formatted": "1. Rute: BTG ➔ JKT\n   - Tipe Truk: TRONTON BOX\n   - Ekspedisi: PT LOGWIN\n   - Customer: WAVIN\n   - Rate: Rp 4.500.000\n   - DP: Rp 0\n   - Uang jalan: Rp 1.800.000\n\n2. Rute: BTG ➔ JKT\n   - Tipe Truk: TRONTON BOX\n   - Ekspedisi: PT LOGWIN\n   - Customer: WAVIN\n   - Rate: Rp 4.500.000\n   - DP: Rp 0\n   - Uang jalan: Rp 2.250.000\n\n3. Rute: BTG ➔ JKT\n   - Tipe Truk: TRONTON BOX\n   - Ekspedisi: PT LOGWIN\n   - Customer: WAVIN\n   - Rate: Rp 4.500.000\n   - DP: Rp 0\n   - Uang jalan: Rp 1.800.000",
          "has_more": false,
          "matched_step": "eksak",
          "message": "Ditemukan 3 data tarif yang cocok.",
          "needs_clarification": [],
          "options": {},
          "rates": [
            {
              "customer_id": 1319,
              "customer_nama": "WAVIN",
              "destinasi": "JKT",
              "destinasi_id": 12,
              "dp": 0,
              "expedisi_id": 452,
              "expedisi_nama": "PT LOGWIN",
              "id": 8463,
              "origin": "BTG",
              "rate": 4500000,
              "status": "published",
              "type_mobil": "TRONTON BOX",
              "type_mobil_id": 29,
              "uang_jalan": 1800000
            },
            {
              "customer_id": 1319,
              "customer_nama": "WAVIN",
              "destinasi": "JKT",
              "destinasi_id": 12,
              "dp": 0,
              "expedisi_id": 452,
              "expedisi_nama": "PT LOGWIN",
              "id": 8530,
              "origin": "BTG",
              "rate": 4500000,
              "status": "published",
              "type_mobil": "TRONTON BOX",
              "type_mobil_id": 29,
              "uang_jalan": 2250000
            },
            {
              "customer_id": 1319,
              "customer_nama": "WAVIN",
              "destinasi": "JKT",
              "destinasi_id": 12,
              "dp": 0,
              "expedisi_id": 452,
              "expedisi_nama": "PT LOGWIN",
              "id": 8730,
              "origin": "BTG",
              "rate": 4500000,
              "status": "published",
              "type_mobil": "TRONTON BOX",
              "type_mobil_id": 29,
              "uang_jalan": 1800000
            }
          ],
          "remaining_count": 0,
          "resolved": {
            "destinasi": [
              "JKT"
            ],
            "mitra": [
              "PT LOGWIN"
            ],
            "origin": [
              "BTG"
            ],
            "type_mobil": [
              "TRONTON BAK",
              "TRONTON BOX"
            ]
          },
          "status": "success",
          "total_found": 3
        },
        "content": "{\"status\": \"success\", \"message\": \"Ditemukan 3 data tarif yang cocok.\", \"formatted\": \"1. Rute: BTG ➔ JKT\\n   - Tipe Truk: TRONTON BOX\\n   - Ekspedisi: PT LOGWIN\\n   - Customer: WAVIN\\n   - Rate: Rp 4.500.000\\n   - DP: Rp 0\\n   - Uang jalan: Rp 1.800.000\\n\\n2. Rute: BTG ➔ JKT\\n   - Tipe Truk: TRONTON BOX\\n   - Ekspedisi: PT LOGWIN\\n   - Customer: WAVIN\\n   - Rate: Rp 4.500.000\\n   - DP: Rp 0\\n   - Uang jalan: Rp 2.250.000\\n\\n3. Rute: BTG ➔ JKT\\n   - Tipe Truk: TRONTON BOX\\n   - Ekspedisi: PT LOGWIN\\n   - Customer: WAVIN\\n   - Rate: Rp 4.500.000\\n   - DP: Rp 0\\n   - Uang jalan: Rp 1.800.000\", \"has_more\": false, \"needs_clarification\": [], \"options\": {}}",
        "id": "9baffd9b-241e-4863-a3f8-f97944d81937",
        "name": "tools_rates",
        "response_metadata": {},
        "status": "success",
        "tool_call_id": "call_163859",
        "type": "tool"
      },
      {
        "additional_kwargs": {},
        "content": [
          {
            "extras": {
              "signature": "El4KXAERTTIPoj/ueHB4R8JH9825EE+x0XEOJtQAdO3Vru76Y5pw47eQx5n2rMuEsDz+3WTEXZOvSjbUL1Qn3m0OSX+TShvn2ZQ9ZxB0uBix//1jfIkAV5YoFXhsYPDu"
            },
            "index": 0,
            "text": "Halo! Berikut adalah rincian rate untuk pengiriman dari Batang (PT. Wavin) tujuan Jakarta (Marunda) via PT Logwin:\n\n1. Rute: BTG ➔ JKT\n   - Tipe Truk: TRONTON BOX\n   - Ekspedisi: PT LOGWIN\n   - Customer: WAVIN\n   - Rate: Rp 4.500.000\n   - DP: Rp 0\n   - Uang jalan: Rp 1.800.000\n\n2. Rute: BTG ➔ JKT\n   - Tipe Truk: TRONTON BOX\n   - Ekspedisi: PT LOGWIN\n   - Customer: WAVIN\n   - Rate: Rp 4.500.000\n   - DP: Rp 0\n   - Uang jalan: Rp 2.250.000\n\n3. Rute: BTG ➔ JKT\n   - Tipe Truk: TRONTON BOX\n   - Ekspedisi: PT LOGWIN\n   - Customer: WAVIN\n   - Rate: Rp 4.500.000\n   - DP: Rp 0\n   - Uang jalan: Rp 1.800.000\n\nSilakan diinfokan jika ada data atau rute lain yang perlu dicheck kembali ya!",
            "type": "text"
          }
        ],
        "id": "lc_run--01a08229-fb71-7a23-aa49-3d6b256af7f4",
        "invalid_tool_calls": [],
        "response_metadata": {
          "finish_reason": "STOP",
          "model_name": "gemini-3.5-flash-lite",
          "model_provider": "google_genai",
          "safety_ratings": []
        },
        "tool_calls": [],
        "type": "ai",
        "usage_metadata": {
          "input_token_details": {
            "cache_read": 0
          },
          "input_tokens": 2170,
          "output_tokens": 301,
          "total_tokens": 2471
        }
      },
      {
        "additional_kwargs": {},
        "content": [
          {
            "text": "BERAPA HARGA RATE DO INI=\n*Shipment PT Wavin Trading Indonesia*\n\n1 x Tronton Bak Terbuka\nMuatan : Pipa (9000mm x 2350mm x 2400mm (50,76 CBM))\n\nEst.Muat : Kamis, 13-Agustus-2026 Jam 07:00\nEst.Bongkar : Jumat, 14-Agustus-2026 Jam 07:00\n\nMuat : \nWavin Trading Indonesia,  Mangunsari, Kedawung, Banyuputih, Batang Regency, Central Java 51271. PIC : Pak Irfan 0878-3095-3566\n\nBongkar :\nSinar Mas Agung\nJl. Genuksari-Karang Roto, Banjardowo, Kec. Genuk, Kota Semarang, Jawa Tengah 50117\nhttps://maps.app.goo.gl/35RrKAiJJ7npURdY8\n",
            "type": "text"
          }
        ],
        "id": "01a0822a-33ba-70bd-b2eb-93d11e888538",
        "response_metadata": {},
        "type": "human"
      },
      {
        "additional_kwargs": {
          "__gemini_function_call_thought_signatures__": {
            "call_341990": "El4KXAERTTIP1qouNRp3JnZwAUmbq3a8PXSbRm0xQppK8FWb6xAc0xzvPt1oWIDx3XCWspOEtgJpBFQBoIOdx2dmhK9oG2GFsizMLZyBZGysQDePgCaev1zyoMCW01Yy"
          },
          "function_call": {
            "arguments": "{\"destinasi\": \"Sinar Mas Agung Jl. Genuksari-Karang Roto, Banjardowo, Kec. Genuk, Kota Semarang, Jawa Tengah 50117\", \"type_mobil\": \"Tronton Bak Terbuka\", \"origin\": \"Wavin Trading Indonesia,  Mangunsari, Kedawung, Banyuputih, Batang Regency, Central Java 51271.\"}",
            "name": "tools_rates"
          }
        },
        "content": [],
        "id": "lc_run--01a0822a-366d-7c13-ba3a-0c5c29410c02",
        "invalid_tool_calls": [],
        "response_metadata": {
          "finish_reason": "STOP",
          "model_name": "gemini-3.5-flash-lite",
          "model_provider": "google_genai",
          "safety_ratings": []
        },
        "tool_calls": [
          {
            "args": {
              "destinasi": "Sinar Mas Agung Jl. Genuksari-Karang Roto, Banjardowo, Kec. Genuk, Kota Semarang, Jawa Tengah 50117",
              "origin": "Wavin Trading Indonesia,  Mangunsari, Kedawung, Banyuputih, Batang Regency, Central Java 51271.",
              "type_mobil": "Tronton Bak Terbuka"
            },
            "id": "call_341990",
            "name": "tools_rates",
            "type": "tool_call"
          }
        ],
        "type": "ai",
        "usage_metadata": {
          "input_token_details": {
            "cache_read": 0
          },
          "input_tokens": 2713,
          "output_tokens": 102,
          "total_tokens": 2815
        }
      },
      {
        "additional_kwargs": {},
        "artifact": {
          "displayed_count": 1,
          "formatted": "1. Rute: BTG ➔ SMG\n   - Tipe Truk: TRONTON BAK\n   - Ekspedisi: PT REMA LOGISTIK INDONESIA (WARESIX)\n   - Customer: WAVIN\n   - Rate: Rp 2.600.000\n   - DP: Rp 0\n   - Uang jalan: Rp 0",
          "has_more": false,
          "matched_step": "eksak",
          "message": "Ditemukan 1 data tarif yang cocok.",
          "needs_clarification": [],
          "options": {},
          "rates": [
            {
              "customer_id": 1319,
              "customer_nama": "WAVIN",
              "destinasi": "SMG",
              "destinasi_id": 3197,
              "dp": 0,
              "expedisi_id": 472,
              "expedisi_nama": "PT REMA LOGISTIK INDONESIA (WARESIX)",
              "id": 9074,
              "origin": "BTG",
              "rate": 2600000,
              "status": "published",
              "type_mobil": "TRONTON BAK",
              "type_mobil_id": 270,
              "uang_jalan": 0
            }
          ],
          "remaining_count": 0,
          "resolved": {
            "destinasi": [
              "SMG"
            ],
            "mitra": [
              "WAVIN"
            ],
            "origin": [
              "BTG"
            ],
            "type_mobil": [
              "TRONTON BAK"
            ]
          },
          "status": "success",
          "total_found": 1
        },
        "content": "{\"status\": \"success\", \"message\": \"Ditemukan 1 data tarif yang cocok.\", \"formatted\": \"1. Rute: BTG ➔ SMG\\n   - Tipe Truk: TRONTON BAK\\n   - Ekspedisi: PT REMA LOGISTIK INDONESIA (WARESIX)\\n   - Customer: WAVIN\\n   - Rate: Rp 2.600.000\\n   - DP: Rp 0\\n   - Uang jalan: Rp 0\", \"has_more\": false, \"needs_clarification\": [], \"options\": {}}",
        "id": "d142bb5c-57e6-4baa-b9ea-e895b8efb4ab",
        "name": "tools_rates",
        "response_metadata": {},
        "status": "success",
        "tool_call_id": "call_341990",
        "type": "tool"
      },
      {
        "additional_kwargs": {},
        "content": [
          {
            "extras": {
              "signature": "El4KXAERTTIPAZdPj5s82XPicqXDhR2m/i7NAAeTWFydDw4LLYEEOh5g9phVAqKA1cL4g8ox6nXe6i9M26sXd4L9//Z2TohHZsZXf8nerD6/YLttqbbMyht0oQ7Lbq/T"
            },
            "index": 0,
            "text": "Berikut adalah rincian rate untuk pengiriman dari Wavin Batang dengan tujuan Sinar Mas Agung Semarang menggunakan Tronton Bak:\n\n1. Rute: BTG ➔ SMG\n   - Tipe Truk: TRONTON BAK\n   - Ekspedisi: PT REMA LOGISTIK INDONESIA (WARESIX)\n   - Customer: WAVIN\n   - Rate: Rp 2.600.000\n   - DP: Rp 0\n   - Uang jalan: Rp 0\n\nAda muatan lain yang perlu saya cekkan ratenya, rekan OPS?",
            "type": "text"
          }
        ],
        "id": "lc_run--01a0822a-3c1c-7202-b770-abda3f1a388a",
        "invalid_tool_calls": [],
        "response_metadata": {
          "finish_reason": "STOP",
          "model_name": "gemini-3.5-flash-lite",
          "model_provider": "google_genai",
          "safety_ratings": []
        },
        "tool_calls": [],
        "type": "ai",
        "usage_metadata": {
          "input_token_details": {
            "cache_read": 0
          },
          "input_tokens": 2942,
          "output_tokens": 127,
          "total_tokens": 3069
        }
      },
      {
        "additional_kwargs": {},
        "content": [
          {
            "text": "sebutkan chat awal saya apa",
            "type": "text"
          }
        ],
        "id": "01a0822a-7fa6-773f-9c57-c0bc1c4142a2",
        "response_metadata": {},
        "type": "human"
      },
      {
        "additional_kwargs": {},
        "content": [
          {
            "extras": {
              "signature": "El4KXAERTTIPdRwkaX6ySreUCF+0WTBOX9Da0v7UfnrQ3+DHbhuOStxVzwulB/dCQHLsriniQ4DXCBr6ETe6LcvLVBdDhGYr3PYAewKTAdkKvsDwiG7Bcj+YzjEmrI2l"
            },
            "index": 0,
            "text": "Chat pertama kamu menanyakan rate untuk pengiriman dengan detail berikut:\n\n- **Armada:** WB\n- **Nopol:** B 9613 UXS\n- **Driver:** Rokib\n- **WA:** 082387396596\n- **Muat:** Grobokan (PT. Pungkook)\n- **Tujuan:** Jakarta\n- **Notes:** Laporan masuk dr Ex : WIDUS/F1",
            "type": "text"
          }
        ],
        "id": "lc_run--01a0822a-83ed-7833-b1eb-d927c0a7dc7b",
        "invalid_tool_calls": [],
        "response_metadata": {
          "finish_reason": "STOP",
          "model_name": "gemini-3.5-flash-lite",
          "model_provider": "google_genai",
          "safety_ratings": []
        },
        "tool_calls": [],
        "type": "ai",
        "usage_metadata": {
          "input_token_details": {
            "cache_read": 0
          },
          "input_tokens": 3078,
          "output_tokens": 99,
          "total_tokens": 3177
        }
      }
    ],
    "slots": {
      "destinasi": [
        "SMG"
      ],
      "mitra": [
        "WAVIN"
      ],
      "origin": [
        "BTG"
      ],
      "type_mobil": [
        "TRONTON BAK"
      ]
    }
  },
  "metadata": {
    "LANGGRAPH_API_URL": "http://127.0.0.1:2024",
    "LANGSMITH_LANGGRAPH_API_VARIANT": "local_dev",
    "LANGSMITH_TRACING": "true",
    "assistant_id": "fe096781-5601-53d2-b2f6-0d3403f7e9ca",
    "checkpoint_id": "1f1abaea-5eae-692b-800d-2b3bc791f865",
    "checkpoint_ns": "",
    "created_by": "system",
    "from_studio": true,
    "graph_id": "agent",
    "langgraph_api_url": "http://127.0.0.1:2024",
    "langgraph_api_version": "0.12.6",
    "langgraph_auth_user_id": "",
    "langgraph_host": "self-hosted",
    "langgraph_plan": "enterprise",
    "langgraph_request_id": "2431fff2-a291-44b7-8172-155bc5fb37c8",
    "langgraph_version": "1.2.11",
    "ls_integration": "langgraph",
    "ls_run_depth": 0,
    "revision_id": "8bddc57-dirty",
    "run_attempt": 1,
    "run_id": "01a0822a-7fd9-7e33-84c3-1fbfef6c892e",
    "thread_id": "01a08229-5a52-7310-bba5-bbd737d6798f",
    "user_id": ""
  },
  "langsmith": {
    "organization": {
      "name": "Personal",
      "id": "fe013f4b-da11-4a36-bb4c-2d8648afd8f8"
    },
    "workspace": {
      "name": "Workspace 1",
      "id": "5eef2592-84a7-4430-9ad3-86cee09732ab"
    },
    "tracing_project": {
      "id": "74a980fc-75bc-4b42-8ecc-f9e380ef4b92",
      "name": "default"
    }
  }
}