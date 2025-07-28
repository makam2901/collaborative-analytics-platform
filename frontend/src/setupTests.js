// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';
window.URL.createObjectURL = function() {};

// Polyfill for the 'HTMLCanvasElement.prototype.getContext' function
HTMLCanvasElement.prototype.getContext = () => {
    // return a mock context object
    return {};
};