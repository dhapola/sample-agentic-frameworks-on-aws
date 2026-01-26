import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Customer } from '../types';
import apiClient from '../services/api';

interface CustomerContextType {
  currentCustomer: Customer | null;
  setCurrentCustomer: (customer: Customer | null) => void;
  isAdmin: boolean;
  setIsAdmin: (isAdmin: boolean) => void;
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
  const [currentCustomer, setCurrentCustomer] = useState<Customer | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);

  // Wire customer context to API client whenever it changes
  useEffect(() => {
    if (currentCustomer) {
      // Set customer context in API client for tenant-scoped requests
      apiClient.setCustomerContext(currentCustomer.id);
      console.log(`Customer context set in API client: ${currentCustomer.id}`);
    } else {
      // Clear customer context when no customer is selected
      apiClient.clearCustomerContext();
      console.log('Customer context cleared from API client');
    }
  }, [currentCustomer]);

  return (
    <CustomerContext.Provider
      value={{
        currentCustomer,
        setCurrentCustomer,
        isAdmin,
        setIsAdmin,
      }}
    >
      {children}
    </CustomerContext.Provider>
  );
};
