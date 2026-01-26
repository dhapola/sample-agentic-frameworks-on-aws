import { renderHook, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { CustomerProvider, useCustomer } from '../../src/contexts/CustomerContext';
import { Customer } from '../../src/types';

describe('CustomerContext', () => {
  const mockCustomer: Customer = {
    id: 'cust1',
    name: 'Test Corp',
    contactEmail: 'test@corp.com',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  };

  test('provides default values', () => {
    const { result } = renderHook(() => useCustomer(), {
      wrapper: CustomerProvider,
    });

    expect(result.current.currentCustomer).toBeNull();
    expect(result.current.isAdmin).toBe(false);
  });

  test('sets current customer', () => {
    const { result } = renderHook(() => useCustomer(), {
      wrapper: CustomerProvider,
    });

    act(() => {
      result.current.setCurrentCustomer(mockCustomer);
    });

    expect(result.current.currentCustomer).toEqual(mockCustomer);
  });

  test('clears current customer', () => {
    const { result } = renderHook(() => useCustomer(), {
      wrapper: CustomerProvider,
    });

    act(() => {
      result.current.setCurrentCustomer(mockCustomer);
    });

    expect(result.current.currentCustomer).toEqual(mockCustomer);

    act(() => {
      result.current.setCurrentCustomer(null);
    });

    expect(result.current.currentCustomer).toBeNull();
  });

  test('sets admin status', () => {
    const { result } = renderHook(() => useCustomer(), {
      wrapper: CustomerProvider,
    });

    act(() => {
      result.current.setIsAdmin(true);
    });

    expect(result.current.isAdmin).toBe(true);
  });

  test('toggles admin status', () => {
    const { result } = renderHook(() => useCustomer(), {
      wrapper: CustomerProvider,
    });

    act(() => {
      result.current.setIsAdmin(true);
    });

    expect(result.current.isAdmin).toBe(true);

    act(() => {
      result.current.setIsAdmin(false);
    });

    expect(result.current.isAdmin).toBe(false);
  });

  test('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const originalError = console.error;
    console.error = jest.fn();

    expect(() => {
      renderHook(() => useCustomer());
    }).toThrow('useCustomer must be used within CustomerProvider');

    console.error = originalError;
  });

  test('maintains customer state across re-renders', () => {
    const { result, rerender } = renderHook(() => useCustomer(), {
      wrapper: CustomerProvider,
    });

    act(() => {
      result.current.setCurrentCustomer(mockCustomer);
    });

    rerender();

    expect(result.current.currentCustomer).toEqual(mockCustomer);
  });

  test('updates customer data', () => {
    const { result } = renderHook(() => useCustomer(), {
      wrapper: CustomerProvider,
    });

    act(() => {
      result.current.setCurrentCustomer(mockCustomer);
    });

    const updatedCustomer = {
      ...mockCustomer,
      name: 'Updated Corp',
    };

    act(() => {
      result.current.setCurrentCustomer(updatedCustomer);
    });

    expect(result.current.currentCustomer?.name).toBe('Updated Corp');
  });
});
