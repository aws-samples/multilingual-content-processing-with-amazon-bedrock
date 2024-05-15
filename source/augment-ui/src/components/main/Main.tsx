import React from "react";
import styled from "styled-components";
import AppData from "components/main/AppData";
import AppNavbar from "components/main/AppNavbar";
// import PdfView from "components/pdf/PdfView";
// import PDFViewer from "components/pdf-viewer/PDFViewer";
import ImageViewer from "components/image-viewer/ImageViewer";
import TableView from "components/table/TableView";
import PDFViewer from "components/pdf-viewer/PDFViewer";
// import { useStoreActions, useStoreState } from "appstore";

const MainContainer = styled.div`
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
`;

const ContentContainer = styled.div`
  width: 100%;
  height: 100%;
  overflow: auto;
  display: flex;
  background: ${(p) => p.theme.gray50};
`;

export default () => {
  // const url = useStoreState((s) => s.documentModel.url);
  // const filename = useStoreState((s) => s.documentModel.filename);
  // const selectedPageNumber = useStoreState(
  //   (s) => s.internal.selectedPageNumber
  // );
  // const numPages = useStoreState((s) => s.documentModel.numPages);
  // const setNumPages = useStoreActions((a) => a.setNumPages);
  // const setSelectedPageNumber = useStoreActions((a) => a.setSelectedPageNumber);
  return (
    <MainContainer>
      <AppData />
      <AppNavbar />
      <ContentContainer>
        <ImageViewer />
        <PDFViewer />
        <TableView />
      </ContentContainer>
    </MainContainer>
  );
};
