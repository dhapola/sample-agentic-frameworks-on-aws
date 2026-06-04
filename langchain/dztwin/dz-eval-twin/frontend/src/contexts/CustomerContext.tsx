import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Customer } from '../types';
import apiClient from '../services/api';

interface CustomerContextType {
  currentCustomer: Customer | null;
  setCurrentCustomer: (customer: Customer | null) => void;
  isAdmin: boolean;
  setIsAdmin: (isAdmin: boolean) => void;
  isReady: boolean;
}

const CustomerContext = createContext<CustomerContextType | undefined>(undefined);

export const useCustomer = () => {
  const context = useContext(CustomerContext);
  if (!context) {
    throw new Error('useCustomer must be used within CustomerProvider');
  }
  return context;
};

interface CustomerProviderProps {
  children: ReactNode;
}

export const CustomerProvider: React.FC<CustomerProviderProps> = ({ children }) => {
  const [currentCustomer, setCurrentCustomer] = useState<Customer | null>(() => {
    // Load from localStorage on mount
    const saved = localStorage.getItem('currentCustomer');
    return saved ? JSON.parse(saved) : null;
  });
  const [isAdmin, setIsAdmin] = useState<boolean>(() => {
    // Load from localStorage on mount
    const saved = localStorage.getItem('isAdmin');
    return saved === 'true';
  });
  const [isReady, setIsReady] = useState<boolean>(false);

  // Initialize API client with saved customer context on mount
  useEffect(() => {
    const saved = localStorage.getItem('currentCustomer');
    if (saved) {
      const customer = JSON.parse(saved);
      apiClient.setCustomerContext(customer.id);
      console.log(`Customer context restored from localStorage: ${customer.id}`);
    }
    // Mark as ready after initialization
    setIsReady(true);
  }, []);

  // Persist customer to localStorage and wire to API client
  useEffect(() => {
    if (currentCustomer) {
      localStorage.setItem('currentCustomer', JSON.stringify(currentCustomer));
      apiClient.setCustomerContext(currentCustomer.id);
      console.log(`Customer context set in API client: ${currentCustomer.id}`);
    } else {
      localStorage.removeItem('currentCustomer');
      apiClient.clearCustomerContext();
      console.log('Customer context cleared from API client');
    }
  }, [currentCustomer]);

  // Persist admin mode to localStorage
  useEffect(() => {
    localStorage.setItem('isAdmin', String(isAdmin));
  }, [isAdmin]);

  return (
    <CustomerContext.Provider
      value={{
        currentCustomer,
        setCurrentCustomer,
        isAdmin,
        setIsAdmin,
        isReady,
      }}
    >
      {children}
    </CustomerContext.Provider>
  );
};
