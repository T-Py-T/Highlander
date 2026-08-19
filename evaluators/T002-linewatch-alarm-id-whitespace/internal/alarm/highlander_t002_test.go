package alarm

import (
	"context"
	"testing"
	"time"
)

func TestHighlanderT002RaiseRejectsPaddedAlarmIDs(t *testing.T) {
	t.Parallel()
	for _, id := range []string{" alarm-001", "alarm-001 ", "\talarm-001"} {
		id := id
		t.Run(id, func(t *testing.T) {
			service := NewService(NewMemoryStore())
			value := Alarm{
				ID:         id,
				Source:     "line-7",
				Code:       "MOTOR_OVERTEMP",
				Severity:   SeverityCritical,
				Message:    "Drive temperature exceeded limit",
				OccurredAt: time.Date(2026, 8, 2, 18, 0, 0, 0, time.UTC),
			}
			if _, err := service.Raise(context.Background(), value); err == nil {
				t.Fatalf("Raise() accepted non-canonical id %q", id)
			}
		})
	}
}

func TestHighlanderT002GetRejectsPaddedIDBeforeStorage(t *testing.T) {
	t.Parallel()
	store := &getTrackingStore{}
	service := NewService(store)
	if _, err := service.Get(context.Background(), " alarm-001 "); err == nil {
		t.Fatal("Get() accepted a non-canonical id")
	}
	if store.getCalled {
		t.Fatal("Get() sent a non-canonical id to storage")
	}
}

type getTrackingStore struct {
	getCalled bool
}

func (*getTrackingStore) Create(context.Context, Alarm) error { return nil }

func (s *getTrackingStore) Get(context.Context, string) (Alarm, error) {
	s.getCalled = true
	return Alarm{}, ErrNotFound
}
