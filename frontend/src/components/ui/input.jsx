import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef(({ className, type, autoComplete, spellCheck, autoCorrect, autoCapitalize, ...props }, ref) => {
  // Determine default autocomplete based on input type and name
  const getDefaultAutoComplete = () => {
    if (autoComplete !== undefined) return autoComplete;
    
    const name = props.name || props.id || '';
    const nameLower = name.toLowerCase();
    
    // Map common field names to autocomplete values
    if (nameLower.includes('email')) return 'email';
    if (nameLower.includes('password')) return 'current-password';
    if (nameLower.includes('new_password') || nameLower.includes('newpassword')) return 'new-password';
    if (nameLower.includes('first') && nameLower.includes('name')) return 'given-name';
    if (nameLower.includes('last') && nameLower.includes('name')) return 'family-name';
    if (nameLower.includes('full') && nameLower.includes('name')) return 'name';
    if (nameLower.includes('name') && !nameLower.includes('company')) return 'name';
    if (nameLower.includes('phone') || nameLower.includes('tel')) return 'tel';
    if (nameLower.includes('company') || nameLower.includes('organization')) return 'organization';
    if (nameLower.includes('title') || nameLower.includes('job')) return 'organization-title';
    if (nameLower.includes('address')) return 'street-address';
    if (nameLower.includes('city')) return 'address-level2';
    if (nameLower.includes('state')) return 'address-level1';
    if (nameLower.includes('zip') || nameLower.includes('postal')) return 'postal-code';
    if (nameLower.includes('country')) return 'country-name';
    if (nameLower.includes('search')) return 'off';
    
    // Type-based defaults
    if (type === 'email') return 'email';
    if (type === 'tel') return 'tel';
    if (type === 'password') return 'current-password';
    if (type === 'search') return 'off';
    
    return 'on';
  };

  // Enable spellcheck for text inputs by default (except passwords, emails, etc.)
  const getDefaultSpellCheck = () => {
    if (spellCheck !== undefined) return spellCheck;
    if (type === 'password' || type === 'email' || type === 'tel' || type === 'number' || type === 'date') return false;
    return true;
  };

  return (
    <input
      type={type}
      className={cn(
        "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        className
      )}
      ref={ref}
      autoComplete={getDefaultAutoComplete()}
      spellCheck={getDefaultSpellCheck()}
      autoCorrect={autoCorrect !== undefined ? autoCorrect : (type === 'password' || type === 'email' ? 'off' : 'on')}
      autoCapitalize={autoCapitalize !== undefined ? autoCapitalize : (type === 'email' || type === 'password' ? 'off' : 'sentences')}
      {...props} />
  );
})
Input.displayName = "Input"

export { Input }
