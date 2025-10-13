import jsPDF from 'jspdf';
import 'jspdf-autotable';
import html2canvas from 'html2canvas';

/**
 * Exports conversation to PDF
 * @param {Object} data - The conversation data to export
 * @param {string} data.query - User's query
 * @param {string} data.answer - AI's response
 * @param {Array} data.queryResults - Query results if available
 * @param {string} data.timestamp - Timestamp of the conversation
 * @param {Object} data.chart - Optional chart data
 */
export const exportToPdf = async (data) => {
  const { query, answer, queryResults, timestamp, chart } = data;
  
  // Create a new PDF document
  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });
  
  // Add title
  pdf.setFontSize(20);
  pdf.setTextColor(0, 0, 0);
  pdf.text('AIUI Conversation Export', 20, 20);
  
  // Add timestamp
  pdf.setFontSize(10);
  pdf.setTextColor(100, 100, 100);
  pdf.text(`Generated on: ${new Date().toLocaleString()}`, 20, 30);
  
  // Add user query section
  pdf.setFontSize(14);
  pdf.setTextColor(0, 0, 0);
  pdf.text('User Query:', 20, 40);
  
  pdf.setFontSize(12);
  pdf.setTextColor(50, 50, 50);
  
  // Split text to handle long lines
  const queryLines = pdf.splitTextToSize(query, 170);
  pdf.text(queryLines, 20, 50);
  
  // Calculate position for answer section based on query length
  let yPosition = 50 + (queryLines.length * 7);
  
  // Add AI response section
  pdf.setFontSize(14);
  pdf.setTextColor(0, 0, 0);
  pdf.text('AI Response:', 20, yPosition);
  
  pdf.setFontSize(12);
  pdf.setTextColor(50, 50, 50);
  
  // Convert markdown to plain text (simplified)
  const plainTextAnswer = answer.replace(/#{1,6}\s?/g, '').replace(/\*\*/g, '');
  
  // Split text to handle long lines
  const answerLines = pdf.splitTextToSize(plainTextAnswer, 170);
  pdf.text(answerLines, 20, yPosition + 10);
  
  // Update position for next section
  yPosition = yPosition + (answerLines.length * 7) + 20;
  
  // Add query results if available
  if (queryResults && queryResults.length > 0) {
    // Add query results section title
    pdf.setFontSize(14);
    pdf.setTextColor(0, 0, 0);
    pdf.text('Query Results:', 20, yPosition);
    
    // Prepare table data
    const tableData = [];
    
    // Get headers from first result
    const headers = Object.keys(queryResults[0]);
    
    // Add rows
    queryResults.forEach(result => {
      const row = [];
      headers.forEach(header => {
        row.push(result[header] !== null && result[header] !== undefined ? result[header].toString() : '');
      });
      tableData.push(row);
    });
    
    // Add table to PDF
    pdf.autoTable({
      startY: yPosition + 5,
      head: [headers],
      body: tableData,
      margin: { top: 20, right: 20, bottom: 20, left: 20 },
      styles: { fontSize: 10, cellPadding: 3 },
      headStyles: { fillColor: [66, 66, 66] }
    });
    
    // Update position after table
    yPosition = pdf.lastAutoTable.finalY + 15;
  }
  
  // Add chart if available
  if (chart && chart.chart_type) {
    try {
      // Find chart element in DOM
      const chartElement = document.querySelector('.apexcharts-canvas');
      if (chartElement) {
        // Add chart title
        pdf.setFontSize(14);
        pdf.setTextColor(0, 0, 0);
        pdf.text('Chart:', 20, yPosition);
        
        // Convert chart to image
        const canvas = await html2canvas(chartElement);
        const imgData = canvas.toDataURL('image/png');
        
        // Add chart image to PDF
        const imgWidth = 170;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        pdf.addImage(imgData, 'PNG', 20, yPosition + 10, imgWidth, imgHeight);
      }
    } catch (error) {
      console.error('Error adding chart to PDF:', error);
    }
  }
  
  // Save the PDF
  pdf.save('aiui-conversation.pdf');
};
