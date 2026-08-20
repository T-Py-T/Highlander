package httpapi

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/T-Py-T/highlander-arena/internal/alarm"
)

func TestHighlanderT002HTTPRejectsPaddedAlarmIDs(t *testing.T) {
	t.Parallel()
	server := New(alarm.NewService(alarm.NewMemoryStore()))

	padded := `{"id":" alarm-001 ","source":"line-7","code":"MOTOR_OVERTEMP","severity":"critical","message":"Drive temperature exceeded limit","occurred_at":"2026-08-02T18:00:00Z"}`
	response := httptest.NewRecorder()
	server.ServeHTTP(response, httptest.NewRequest(http.MethodPost, "/v1/alarms", strings.NewReader(padded)))
	assertHighlanderT002Error(t, response, http.StatusBadRequest, "invalid_alarm")

	canonical := `{"id":"alarm-001","source":"line-7","code":"MOTOR_OVERTEMP","severity":"critical","message":"Drive temperature exceeded limit","occurred_at":"2026-08-02T18:00:00Z"}`
	response = httptest.NewRecorder()
	server.ServeHTTP(response, httptest.NewRequest(http.MethodPost, "/v1/alarms", strings.NewReader(canonical)))
	if response.Code != http.StatusCreated {
		t.Fatalf("canonical POST status = %d, body = %s", response.Code, response.Body.String())
	}

	response = httptest.NewRecorder()
	server.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/v1/alarms/%20alarm-001%20", nil))
	assertHighlanderT002Error(t, response, http.StatusBadRequest, "invalid_id")
}

func assertHighlanderT002Error(t *testing.T, response *httptest.ResponseRecorder, status int, code string) {
	t.Helper()
	if response.Code != status {
		t.Fatalf("status = %d, want %d; body = %s", response.Code, status, response.Body.String())
	}
	var body map[string]string
	if err := json.NewDecoder(response.Body).Decode(&body); err != nil {
		t.Fatalf("decode error response: %v", err)
	}
	if body["code"] != code {
		t.Fatalf("error code = %q, want %q", body["code"], code)
	}
}
