export const jobData = [
  { value: "0", label: "Admin" },
  { value: "9", label: "Technician" },
  { value: "7", label: "Services" },
  { value: "4", label: "Management" },
  { value: "5", label: "Retired" },
  { value: "1", label: "Blue-collar" },
  { value: "10", label: "Unemployed" },
  { value: "2", label: "Entrepreneur" },
  { value: "3", label: "Housemaid" },
  { value: "11", label: "Unknown" },
  { value: "6", label: "Self-employed" },
  { value: "8", label: "Student" },
];

export const educationData = [
  { value: "0", label: "Primary" },
  { value: "1", label: "Secondary" },
  { value: "2", label: "Tertiary" },
  { value: "3", label: "Unknown" },
];

export const maritalStatusData = [
  { value: "2", label: "Single" },
  { value: "1", label: "Married" },
  { value: "0", label: "Divorced" },
];

export const phoneData = [
  { value: "2", label: "Unknown" },
  { value: "0", label: "Cellular" },
  { value: "1", label: "Telephone" },
];

export const loanData = [
  { value: "1", label: "Yes" },
  { value: "0", label: "No" },
];

export const housingData = [
  { value: "1", label: "Yes" },
  { value: "0", label: "No" },
];

export const defaultData = [
  { value: "1", label: "Yes" },
  { value: "0", label: "No" },
];

export const dayData = Array.from({ length: 31 }, (_, i) => ({
  value: String(i + 1),
  label: String(i + 1),
}));

export const monthData = [
  { value: "4", label: "January" },
  { value: "3", label: "February" },
  { value: "7", label: "March" },
  { value: "0", label: "April" },
  { value: "8", label: "May" },
  { value: "6", label: "June" },
  { value: "5", label: "July" },
  { value: "1", label: "August" },
  { value: "11", label: "September" },
  { value: "10", label: "October" },
  { value: "9", label: "November" },
  { value: "2", label: "December" },
];

export const previousOutcomeData = [
  { value: "2", label: "Success" },
  { value: "0", label: "Failure" },
  { value: "1", label: "Other" },
  { value: "3", label: "Unknown" },
];
